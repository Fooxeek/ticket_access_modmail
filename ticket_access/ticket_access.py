"""
Plugin Ticket Access - ModMail
Permet d'ajouter ou de retirer un membre du staff sur un ticket en cours,
en modifiant les permissions du canal Discord associé au thread ModMail.

Seuls les membres possédant le rôle HELPER_ROLE_ID (défini ci-dessous)
peuvent être ajoutés/retirés d'un ticket via ces commandes.

COMMANDES :
  ?addtoticket <membre>        — Donne accès au ticket courant (MODERATOR)
  ?removefromticket <membre>   — Retire l'accès au ticket courant (MODERATOR)
"""
import discord
from discord.ext import commands
from core import checks
from core.models import PermissionLevel

# ID du rôle requis pour qu'un membre puisse être ajouté/retiré d'un ticket.
HELPER_ROLE_ID = 326464995682418688

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

    def _get_helper_role(self, ctx) -> discord.Role:
        return ctx.guild.get_role(HELPER_ROLE_ID)

    def _check_role(self, ctx, member: discord.Member):
        """Retourne (ok, helper_role). ok=False si le rôle est introuvable ou absent du membre."""
        helper_role = self._get_helper_role(ctx)
        if helper_role is None:
            return False, None
        return (helper_role in member.roles), helper_role

    # ── Commande d'ajout ───────────────────────────────────────────────────

    @commands.command(name="addtoticket")
    @checks.has_permissions(PermissionLevel.MODERATOR)
    async def add_to_ticket(self, ctx, member: discord.Member):
        """Ajoute un membre au ticket courant (accès lecture/écriture au canal)."""
        ok, helper_role = self._check_role(ctx, member)
        if helper_role is None:
            await self._send_error(
                ctx, "❌ Rôle introuvable",
                f"Le rôle configuré (ID `{HELPER_ROLE_ID}`) n'existe pas sur ce serveur.",
            )
            return
        if not ok:
            await self._send_error(
                ctx, "❌ Rôle requis manquant",
                f"{member.mention} n'a pas le rôle {helper_role.mention}, requis pour être ajouté à un ticket.",
            )
            return

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
                "Le bot n'a pas la permission `Gérer les rôles` sur ce canal.",
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

    @commands.command(name="removefromticket")
    @checks.has_permissions(PermissionLevel.MODERATOR)
    async def remove_from_ticket(self, ctx, member: discord.Member):
        """Retire l'accès d'un membre au ticket courant."""
        ok, helper_role = self._check_role(ctx, member)
        if helper_role is None:
            await self._send_error(
                ctx, "❌ Rôle introuvable",
                f"Le rôle configuré (ID `{HELPER_ROLE_ID}`) n'existe pas sur ce serveur.",
            )
            return
        if not ok:
            await self._send_error(
                ctx, "❌ Rôle requis manquant",
                f"{member.mention} n'a pas le rôle {helper_role.mention}. "
                f"Seuls les membres avec ce rôle peuvent être gérés via cette commande.",
            )
            return

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
                "Le bot n'a pas la permission `Gérer les rôles` sur ce canal.",
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