from typing import Dict

import nextcord
from nextcord.ext import commands

from pie import check, logger, utils, i18n

_ = i18n.Translator("modules/private").translate
bot_log = logger.Bot.logger()


class Halloween2021(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.check(check.acl)
    @commands.group()
    async def halloween(self, ctx):
        await utils.discord.send_help(ctx)

    @halloween.command(name="color")
    async def halloween_color(self, ctx):
        roles = [r for r in ctx.guild.roles if r.is_assignable()]

        colors: Dict[int, int] = {}
        async with ctx.typing():
            for role in roles:
                color = (
                    int(role.color)
                    if type(role.color) is nextcord.Color
                    else role.color.value
                )
                if color == 0:
                    continue

                colors[role.id] = int(color)
                await role.edit(color=0xDD9B0D)

        message: str = _(ctx, "Keep this, you will need it to revert the colors back:")
        output: str = ",".join(f"{k}:{v}" for k, v in colors.items())
        print(output)
        await ctx.reply(message + "\n> " + output)

    @halloween.command(name="uncolor")
    async def halloween_uncolor(self, ctx, data: str):
        colors: Dict[int, int] = {}
        for role_data in data.split(","):
            role, color = role_data.split(":")
            colors[int(role)] = int(color)

        async with ctx.typing():
            for role in ctx.guild.roles:
                if role.id in colors.keys():
                    await role.edit(color=colors[role.id])

        await ctx.reply(_(ctx, "Role colors have been reverted back."))


def setup(bot) -> None:
    bot.add_cog(Halloween2021(bot))
