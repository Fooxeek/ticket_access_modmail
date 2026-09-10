"""
Plugin Ticket Access - ModMail
Permet d'ajouter ou de retirer un membre du staff sur un ticket en cours,
en modifiant les permissions du canal Discord associé au thread ModMail.

COMMANDES :
  ?addtoticket <membre>     — Donne accès au ticket courant (MODERATOR)
  ?removetoticket <membre>  — Retire l'accès au ticket courant (MODERATOR)
"""
import discord
from discord.ext import commands
from core import checks
from core.models import PermissionLevel

COLOR_SUCCESS = discord.Color.green()
COLOR_INFO = discord.Color.blue()
COLOR_WARNING = discord.Color.orange()
COLOR_DANGER = discord.Color.red()


class TicketAccess(commands.Cog):
    """Gère l'ajout/le retrait de membres sur un canal de ticket ModMail."""

    def __init__(self, bot):
        self.bot = bot

    async def _get_thread(self, ctx):
        """Vérifie que la commande est utilisée dans un canal de ticket ModMail."""
        return await self.bot.threads.find(channel=ctx.channel)

    async def _send_error(self, ctx, title: str, description: str):
        await ctx.send(embed=discord.Embed(title=title, description=description, color=COLOR_DANGER))

    # ── Commande d'ajout ───────────────────────────────────────────────────

    @commands.command(name="addtoticket")
    @checks.has_permissions(PermissionLevel.MODERATOR)
    async def add_to_ticket(self, ctx, member: discord.Member):
        """Ajoute un membre au ticket courant (accès lecture/écriture au canal)."""
        thread = await self._get_thread(ctx)
        if not thread:
            await self._send_error(
                ctx, "❌ Hors contexte",
                "Cette commande doit être utilisée dans un canal de ticket ModMail.",
            )
            return

        channel = thread.channel
        overwrite = channel.overwrites_for(member)

        if overwrite.read_messages:
            await ctx.send(embed=discord.Embed(
                title="ℹ️ Déjà ajouté",
                description=f"{member.mention} a déjà accès à ce ticket.",
                color=COLOR_INFO,
            ))
            return

        try:
            await channel.set_permissions(
                member,
                read_messages=True,
                send_messages=True,
                read_message_history=True,
                reason=f"Ajouté au ticket par {ctx.author} ({ctx.author.id})",
            )
        except discord.Forbidden:
            await self._send_error(
                ctx, "❌ Permission refusée",
                "Le bot n'a pas la permission `Gérer les salons` sur ce canal.",
            )
            return
        except discord.HTTPException as e:
            await self._send_error(ctx, "❌ Erreur", f"Impossible de modifier les accès : {e}")
            return

        await ctx.send(embed=discord.Embed(
            title="✅ Membre ajouté au ticket",
            description=f"{member.mention} peut désormais voir et suivre l'avancée de ce ticket.",
            color=COLOR_SUCCESS,
        ))

        try:
            await member.send(
                f"Vous avez été ajouté au ticket **{channel.name}** sur **{ctx.guild.name}**. "
                f"Vous pouvez le consulter ici : {channel.mention}"
            )
        except (discord.Forbidden, discord.HTTPException):
            pass  # DMs fermés, on ignore silencieusement

    # ── Commande de retrait ────────────────────────────────────────────────

    @commands.command(name="removetoticket")
    @checks.has_permissions(PermissionLevel.MODERATOR)
    async def remove_from_ticket(self, ctx, member: discord.Member):
        """Retire l'accès d'un membre au ticket courant."""
        thread = await self._get_thread(ctx)
        if not thread:
            await self._send_error(
                ctx, "❌ Hors contexte",
                "Cette commande doit être utilisée dans un canal de ticket ModMail.",
            )
            return

        channel = thread.channel
        overwrite = channel.overwrites_for(member)

        if not overwrite.read_messages:
            await ctx.send(embed=discord.Embed(
                title="ℹ️ Aucun accès à retirer",
                description=f"{member.mention} n'a pas d'accès explicite à ce ticket.",
                color=COLOR_INFO,
            ))
            return

        try:
            await channel.set_permissions(
                member,
                overwrite=None,
                reason=f"Retiré du ticket par {ctx.author} ({ctx.author.id})",
            )
        except discord.Forbidden:
            await self._send_error(
                ctx, "❌ Permission refusée",
                "Le bot n'a pas la permission `Gérer les salons` sur ce canal.",
            )
            return
        except discord.HTTPException as e:
            await self._send_error(ctx, "❌ Erreur", f"Impossible de modifier les accès : {e}")
            return

        await ctx.send(embed=discord.Embed(
            title="✅ Membre retiré du ticket",
            description=f"{member.mention} n'a plus accès à ce ticket.",
            color=COLOR_WARNING,
        ))


async def setup(bot):
    """Chargement du Cog."""
    await bot.add_cog(TicketAccess(bot))