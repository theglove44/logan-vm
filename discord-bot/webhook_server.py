#!/usr/bin/env python3
"""
Webhook Server for Media Server Discord Bot

Receives HTTP webhooks from Sonarr, Radarr, and Overseerr.
Routes notifications to organized Discord channels with rich embeds.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

import discord
from aiohttp import web

logger = logging.getLogger('webhook_server')

# ============================================================================
# EVENT ROUTING TABLES
# ============================================================================

# Sonarr/Radarr event type -> (channel_name, color, emoji, title_suffix)
ARR_EVENT_ROUTING = {
    'Grab':                      ('ms-downloading', 0xF1C40F, '\u2b07\ufe0f',  'Grabbed'),
    'Download':                  ('ms-completed',   0x2ECC71, '\u2705',  'Imported'),
    'ManualInteractionRequired': ('ms-attention',   0xE67E22, '\u26a0\ufe0f',  'Manual Interaction Required'),
    'HealthIssue':               ('ms-attention',   0xE74C3C, '\u274c',  'Health Issue'),
    'HealthRestored':            ('ms-system',      0x2ECC71, '\U0001f49a',  'Health Restored'),
    'ApplicationUpdate':         ('ms-system',      0x3498DB, '\U0001f504',  'Application Update'),
    'Test':                      ('ms-system',      0x95A5A6, '\U0001f9ea',  'Test Notification'),
    'Rename':                    ('ms-system',      0x95A5A6, '\U0001f4dd',  'Renamed'),
    'SeriesAdd':                 ('ms-system',      0x3498DB, '\u2795',  'Series Added'),
    'SeriesDelete':              ('ms-system',      0xE74C3C, '\U0001f5d1\ufe0f',  'Series Deleted'),
    'MovieAdded':                ('ms-system',      0x3498DB, '\u2795',  'Movie Added'),
    'MovieDelete':               ('ms-system',      0xE74C3C, '\U0001f5d1\ufe0f',  'Movie Deleted'),
    'MovieFileDelete':           ('ms-system',      0xE74C3C, '\U0001f5d1\ufe0f',  'Movie File Deleted'),
    'EpisodeFileDelete':         ('ms-system',      0xE74C3C, '\U0001f5d1\ufe0f',  'Episode File Deleted'),
}

# Overseerr notification type -> (channel_name, color, emoji, title_suffix)
OVERSEERR_EVENT_ROUTING = {
    'MEDIA_PENDING':       ('ms-requests',  0x3498DB, '\U0001f3ac', 'Media Requested'),
    'MEDIA_APPROVED':      ('ms-requests',  0x2ECC71, '\u2705', 'Request Approved'),
    'MEDIA_AUTO_APPROVED': ('ms-requests',  0x2ECC71, '\u2705', 'Auto-Approved'),
    'MEDIA_AVAILABLE':     ('ms-completed', 0x2ECC71, '\U0001f389', 'Now Available'),
    'MEDIA_DECLINED':      ('ms-attention', 0xE74C3C, '\u274c', 'Request Declined'),
    'MEDIA_FAILED':        ('ms-attention', 0xE74C3C, '\u274c', 'Request Failed'),
    'TEST_NOTIFICATION':   ('ms-system',    0x95A5A6, '\U0001f9ea', 'Test Notification'),
}


# ============================================================================
# HELPERS
# ============================================================================

def format_size(size_bytes):
    """Format bytes to human-readable size."""
    if not size_bytes:
        return "?"
    try:
        size = float(size_bytes)
    except (ValueError, TypeError):
        return "?"
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if abs(size) < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"


def _extract_quality(quality_field):
    """Extract quality name from nested or string quality field."""
    if isinstance(quality_field, dict):
        inner = quality_field.get('quality', quality_field)
        if isinstance(inner, dict):
            return inner.get('name', '?')
        return str(inner)
    if quality_field:
        return str(quality_field)
    return "?"


# ============================================================================
# WEBHOOK SERVER
# ============================================================================

class WebhookServer:
    """HTTP server that receives webhooks and routes them to Discord channels."""

    def __init__(self, channel_mgr, poster_cache, http_session, port=9999):
        self.channel_mgr = channel_mgr
        self.poster_cache = poster_cache
        self.http_session = http_session
        self.port = port
        self.is_running = False

        self.app = web.Application()
        self.app.router.add_post('/webhook/sonarr', self.handle_sonarr)
        self.app.router.add_post('/webhook/radarr', self.handle_radarr)
        self.app.router.add_post('/webhook/overseerr', self.handle_overseerr)
        self.app.router.add_get('/health', self.handle_health)

        self.runner = None

    async def start(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, '0.0.0.0', self.port)
        await site.start()
        self.is_running = True
        logger.info(f"Webhook server listening on 0.0.0.0:{self.port}")

    async def stop(self):
        if self.runner:
            await self.runner.cleanup()
        self.is_running = False
        logger.info("Webhook server stopped")

    # ------------------------------------------------------------------
    # Route handlers
    # ------------------------------------------------------------------

    async def handle_health(self, request):
        return web.json_response({
            "status": "ok",
            "channels": len(self.channel_mgr.channels),
        })

    async def handle_sonarr(self, request):
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"status": "error", "message": "invalid JSON"}, status=400)

        event_type = data.get('eventType', 'Unknown')
        logger.info(f"Sonarr webhook received: {event_type}")

        routing = ARR_EVENT_ROUTING.get(event_type)
        if not routing:
            logger.warning(f"Unknown Sonarr event type: {event_type}")
            return web.json_response({"status": "ignored", "event": event_type})

        channel_name, color, emoji, title_suffix = routing
        channel = self.channel_mgr.get(channel_name)
        if not channel:
            logger.error(f"Channel {channel_name} not found")
            return web.json_response({"status": "error", "message": "channel not found"}, status=500)

        try:
            embed = await self._build_sonarr_embed(data, event_type, color, emoji, title_suffix)
            await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to send Sonarr embed: {e}", exc_info=True)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

        return web.json_response({"status": "ok"})

    async def handle_radarr(self, request):
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"status": "error", "message": "invalid JSON"}, status=400)

        event_type = data.get('eventType', 'Unknown')
        logger.info(f"Radarr webhook received: {event_type}")

        routing = ARR_EVENT_ROUTING.get(event_type)
        if not routing:
            logger.warning(f"Unknown Radarr event type: {event_type}")
            return web.json_response({"status": "ignored", "event": event_type})

        channel_name, color, emoji, title_suffix = routing
        channel = self.channel_mgr.get(channel_name)
        if not channel:
            logger.error(f"Channel {channel_name} not found")
            return web.json_response({"status": "error", "message": "channel not found"}, status=500)

        try:
            embed = await self._build_radarr_embed(data, event_type, color, emoji, title_suffix)
            await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to send Radarr embed: {e}", exc_info=True)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

        return web.json_response({"status": "ok"})

    async def handle_overseerr(self, request):
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"status": "error", "message": "invalid JSON"}, status=400)

        notif_type = data.get('notification_type', 'Unknown')
        logger.info(f"Overseerr webhook received: {notif_type}")

        routing = OVERSEERR_EVENT_ROUTING.get(notif_type)
        if not routing:
            logger.warning(f"Unknown Overseerr notification type: {notif_type}")
            return web.json_response({"status": "ignored", "event": notif_type})

        channel_name, color, emoji, title_suffix = routing
        channel = self.channel_mgr.get(channel_name)
        if not channel:
            logger.error(f"Channel {channel_name} not found")
            return web.json_response({"status": "error", "message": "channel not found"}, status=500)

        try:
            embed = self._build_overseerr_embed(data, notif_type, color, emoji, title_suffix)
            await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to send Overseerr embed: {e}", exc_info=True)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

        return web.json_response({"status": "ok"})

    # ------------------------------------------------------------------
    # Embed builders
    # ------------------------------------------------------------------

    async def _build_sonarr_embed(self, data, event_type, color, emoji, title_suffix):
        embed = discord.Embed(
            title=f"{emoji} Sonarr | {title_suffix}",
            color=color,
            timestamp=datetime.now(timezone.utc),
        )

        series = data.get('series', {})
        episodes = data.get('episodes', [])
        release = data.get('release', {})

        # Series title
        title = series.get('title', 'Unknown')
        year = series.get('year')
        if year:
            title = f"{title} ({year})"
        embed.add_field(name="Series", value=title, inline=True)

        # Episode info
        if episodes:
            ep = episodes[0]
            s = ep.get('seasonNumber', '?')
            e = ep.get('episodeNumber', '?')
            ep_title = ep.get('title', '')
            ep_str = f"S{s:02d}E{e:02d}" if isinstance(s, int) and isinstance(e, int) else f"S{s}E{e}"
            if ep_title:
                ep_str += f" - {ep_title}"
            embed.add_field(name="Episode", value=ep_str, inline=True)

        # Grab fields
        if event_type == 'Grab':
            quality = _extract_quality(release.get('quality'))
            embed.add_field(name="Quality", value=quality, inline=True)

            size = release.get('size')
            if size:
                embed.add_field(name="Size", value=format_size(size), inline=True)

            indexer = release.get('indexer', '')
            if indexer:
                embed.add_field(name="Indexer", value=indexer, inline=True)

        # Import fields
        if event_type == 'Download':
            ep_file = data.get('episodeFile', {})
            quality = _extract_quality(ep_file.get('quality'))
            embed.add_field(name="Quality", value=quality, inline=True)

            size = ep_file.get('size')
            if size:
                embed.add_field(name="Size", value=format_size(size), inline=True)

            is_upgrade = data.get('isUpgrade', False)
            if is_upgrade:
                embed.add_field(name="Upgrade", value="Yes", inline=True)

        # Manual interaction
        if event_type == 'ManualInteractionRequired':
            dl_info = data.get('downloadInfo', {})
            detail = dl_info.get('title', '') or data.get('message', 'Requires manual import')
            embed.add_field(name="Status", value="Requires manual import", inline=True)
            if detail:
                embed.add_field(name="Details", value=detail[:200], inline=False)

        # Health events
        if event_type in ('HealthIssue', 'HealthRestored'):
            health_type = data.get('type', '')
            msg = data.get('message', '')
            if health_type:
                embed.add_field(name="Type", value=health_type, inline=True)
            if msg:
                embed.add_field(name="Message", value=msg[:500], inline=False)

        # Application update
        if event_type == 'ApplicationUpdate':
            prev = data.get('previousVersion', '')
            new = data.get('newVersion', '')
            if prev and new:
                embed.add_field(name="Update", value=f"{prev} -> {new}", inline=True)

        # Poster thumbnail
        poster_url = await self._get_poster('sonarr', series.get('id'), series.get('images', []))
        if poster_url:
            embed.set_thumbnail(url=poster_url)

        embed.set_footer(text="Sonarr")
        return embed

    async def _build_radarr_embed(self, data, event_type, color, emoji, title_suffix):
        embed = discord.Embed(
            title=f"{emoji} Radarr | {title_suffix}",
            color=color,
            timestamp=datetime.now(timezone.utc),
        )

        movie = data.get('movie', {})
        release = data.get('release', {})

        # Movie title
        title = movie.get('title', 'Unknown')
        year = movie.get('year')
        if year:
            title = f"{title} ({year})"
        embed.add_field(name="Movie", value=title, inline=True)

        # Grab fields
        if event_type == 'Grab':
            quality = _extract_quality(release.get('quality'))
            embed.add_field(name="Quality", value=quality, inline=True)

            size = release.get('size')
            if size:
                embed.add_field(name="Size", value=format_size(size), inline=True)

            indexer = release.get('indexer', '')
            if indexer:
                embed.add_field(name="Indexer", value=indexer, inline=True)

        # Import fields
        if event_type == 'Download':
            movie_file = data.get('movieFile', {})
            quality = _extract_quality(movie_file.get('quality'))
            embed.add_field(name="Quality", value=quality, inline=True)

            size = movie_file.get('size')
            if size:
                embed.add_field(name="Size", value=format_size(size), inline=True)

            is_upgrade = data.get('isUpgrade', False)
            if is_upgrade:
                embed.add_field(name="Upgrade", value="Yes", inline=True)

        # Manual interaction
        if event_type == 'ManualInteractionRequired':
            dl_info = data.get('downloadInfo', {})
            detail = dl_info.get('title', '') or data.get('message', 'Requires manual import')
            embed.add_field(name="Status", value="Requires manual import", inline=True)
            if detail:
                embed.add_field(name="Details", value=detail[:200], inline=False)

        # Health events
        if event_type in ('HealthIssue', 'HealthRestored'):
            health_type = data.get('type', '')
            msg = data.get('message', '')
            if health_type:
                embed.add_field(name="Type", value=health_type, inline=True)
            if msg:
                embed.add_field(name="Message", value=msg[:500], inline=False)

        # Application update
        if event_type == 'ApplicationUpdate':
            prev = data.get('previousVersion', '')
            new = data.get('newVersion', '')
            if prev and new:
                embed.add_field(name="Update", value=f"{prev} -> {new}", inline=True)

        # Poster thumbnail
        poster_url = await self._get_poster('radarr', movie.get('id'), movie.get('images', []))
        if poster_url:
            embed.set_thumbnail(url=poster_url)

        embed.set_footer(text="Radarr")
        return embed

    def _build_overseerr_embed(self, data, notif_type, color, emoji, title_suffix):
        embed = discord.Embed(
            title=f"{emoji} Overseerr | {title_suffix}",
            color=color,
            timestamp=datetime.now(timezone.utc),
        )

        subject = data.get('subject', '')
        message = data.get('message', '')
        media = data.get('media') or {}
        request_data = data.get('request') or {}

        if subject:
            embed.add_field(name="Title", value=subject, inline=True)

        media_type = media.get('media_type', '')
        if media_type:
            embed.add_field(name="Type", value=media_type.title(), inline=True)

        requested_by = (
            request_data.get('requestedBy_username', '')
            or request_data.get('requestedBy_displayname', '')
        )
        if requested_by:
            embed.add_field(name="Requested By", value=requested_by, inline=True)

        status_val = media.get('status', '')
        if status_val:
            status_labels = {1: 'Unknown', 2: 'Pending', 3: 'Processing', 4: 'Partially Available', 5: 'Available'}
            embed.add_field(name="Status", value=status_labels.get(status_val, str(status_val)), inline=True)

        if message and message != subject:
            embed.add_field(name="Details", value=message[:500], inline=False)

        # Poster image from Overseerr payload
        image = data.get('image', '')
        if image:
            if image.startswith('http'):
                embed.set_thumbnail(url=image)
            else:
                embed.set_thumbnail(url=f"https://image.tmdb.org/t/p/w300{image}")

        embed.set_footer(text="Overseerr")
        return embed

    # ------------------------------------------------------------------
    # Poster helper
    # ------------------------------------------------------------------

    async def _get_poster(self, source, media_id, images=None):
        """Get poster URL via shared PosterCache."""
        return await self.poster_cache.get_poster_url(
            self.http_session, source, media_id, images
        )
