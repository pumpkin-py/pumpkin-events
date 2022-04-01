import datetime
import io
import random
from typing import Callable, Dict, List, Set, Optional

import pygal

import nextcord
from nextcord.ext import commands, tasks

import pie._tracing
from pie import check, i18n, logger, utils

from .database import InfectionConfig, Infected

_ = i18n.Translator("modules/events").translate
bot_log = logger.Bot.logger()
guild_log = logger.Guild.logger()

_trace: Callable = pie._tracing.register("private_infection")


class Infection(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.guilds: Set[int] = InfectionConfig.get_guild_ids()
        self.message_cache: Dict[nextcord.Channel, nextcord.Message] = {}

        self.infection_loop.start()

    #

    def cog_unload(self):
        self.infection_loop.cancel()

    @tasks.loop(minutes=5)
    async def infection_loop(self):
        _trace("Running infection loop.")
        spreaders = Infected.get_spreaders()
        configs = {c.guild_id: c for c in InfectionConfig.get_all()}
        now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)

        for spreader in spreaders:
            config = configs[spreader.guild_id]
            guild = self.bot.get_guild(spreader.guild_id)

            member = guild.get_member(spreader.user_id)
            if not member:
                await guild_log.debug(
                    self.bot.user,
                    guild.text_channels[0],
                    f"Could not find user {spreader.user_id}.",
                )
                continue

            role = guild.get_role(config.role_id)
            if not role:
                await guild_log.error(
                    self.bot.user,
                    guild.text_channels[0],
                    f"Could not find role {config.role_id}.",
                )
                continue

            delta: datetime.timedelta = now - spreader.infected_at

            if delta > config.symptom_delay and not spreader.cured:
                # Add symptoms, if there weren't before
                spreader.symptomatic = True
                if role not in member.roles and not config.quiet:
                    try:
                        await member.add_roles(role, reason="Infection")
                        await guild_log.info(
                            self.bot.user,
                            guild.text_channels[0],
                            f"Adding infected role to {member}.",
                        )
                    except nextcord.Forbidden:
                        await guild_log.debug(
                            self.bot.user,
                            guild.text_channels[0],
                            f"Cannot add role {role} to {member}: permission denied.",
                        )
            elif delta < config.cure_delay:
                _trace(
                    f"Member {member}@{member.guild.name} without symptoms so far, "
                    f"delta {delta} < {config.symptom_delay}."
                )
            if delta > config.cure_delay:
                # Remove symptoms, the member is cured
                spreader.symptomatic = False
                spreader.cured = True
                if role in member.roles and not config.quiet:
                    try:
                        await member.remove_roles(role, reason="Cured")
                    except nextcord.Forbidden:
                        await guild_log.debug(
                            self.bot.user,
                            guild.text_channels[0],
                            f"Cannot remove role {role} from {member}: permission denied.",
                        )
                    await guild_log.info(
                        self.bot.user,
                        guild.text_channels[0],
                        f"Removing infected role from {member}@{member.guild.name}.",
                    )
            elif delta > config.symptom_delay:
                _trace(
                    f"Member {member}@{member.guild.name} with symptoms so far, "
                    f"delta {delta} < {config.cure_delay}."
                )
            spreader.save()

    @infection_loop.before_loop
    async def before_infection_loop(self):
        if not self.bot.is_ready():
            await self.bot.wait_until_ready()

    #

    @commands.guild_only()
    @check.acl2(check.ACLevel.MEMBER)
    @commands.group(name="infection")
    async def infection_(self, ctx):
        """A virus?!"""
        await utils.discord.send_help(ctx)

    @check.acl2(check.ACLevel.MEMBER)
    @infection_.command(name="check")
    async def infection_check(self, ctx):
        """Check for infection."""
        infected: bool
        user = Infected.get(ctx.guild.id, ctx.author.id)
        if not user or (not user.symptomatic and not user.cured):
            await ctx.reply(_(ctx, "You don't seem to have any symptoms."))
            return
        if user.symptomatic:
            status = ""
            await ctx.reply(
                status
                + "\n"
                + _(ctx, "Be careful, make sure you don't infect anyone else.")
            )
            return

        embed = utils.discord.create_embed(
            author=ctx.author,
            title=_(ctx, "Health check"),
            description=_(ctx, "You can't get infected by the virus anymore."),
        )
        embed.add_field(
            name=_(ctx, "Infected at"),
            value=utils.time.format_datetime(user.infected_at),
            inline=False,
        )
        if user.infected_by == 0:
            infected_by_name = _(ctx, "You are patient zero.")
        else:
            infected_by = self.bot.get_user(user.infected_by)
            infected_by_name = getattr(infected_by, "name", user.infected_by)
        message = await utils.discord.get_message(
            self.bot, user.guild_id, user.channel_id, user.message_id
        )
        message_link: str
        if message:
            message_link = f"[#{message.channel.name}]({message.jump_url})"
        else:
            message_link = _(ctx, "No message")
        embed.add_field(
            name=_(ctx, "Infected by"),
            value=message_link + "\n" + infected_by_name,
            inline=False,
        )

        await ctx.reply(embed=embed)

    @check.acl2(check.ACLevel.MOD)
    @infection_.command(name="list")
    async def infection_list(self, ctx):
        """List infected members."""
        users = Infected.get_all(ctx.guild.id)

        class Item:
            def __init__(self, bot: commands.Bot, user: Infected):
                dc_user = bot.get_user(user.user_id)
                self.name = getattr(dc_user, "name", user.user_id)
                self.infected_at = utils.time.format_datetime(user.infected_at)
                if user.infected_by == 0:
                    self.infected_by = _(ctx, "(patient zero)")
                else:
                    infected_by = bot.get_user(user.infected_by)
                    self.infected_by = getattr(infected_by, "name", user.infected_by)
                if not user.symptomatic and not user.cured:
                    self.status = _(ctx, "Asymptomatic")
                elif not user.cured:
                    self.status = _(ctx, "Symptomatic")
                else:
                    self.status = _(ctx, "Cured")

        items = [Item(self.bot, user) for user in users]
        table: List[str] = utils.text.create_table(
            items,
            header={
                "name": _(ctx, "Name"),
                "infected_at": _(ctx, "Infected at"),
                "infected_by": _(ctx, "Infected by"),
                "status": _(ctx, "Status"),
            },
        )

        for page in table:
            await ctx.send("```" + page + "```")

    @check.acl2(check.ACLevel.MOD)
    @infection_.command(name="graph")
    async def infection_graph(self, ctx):
        """Show infection graphs."""
        everyone = Infected.get_all(ctx.guild.id)
        if not everyone:
            await ctx.reply(_(ctx, "No one has been infected."))
            return

        zero: datetime.datetime = everyone[0].infected_at
        infected: Dict[int, int] = {}

        async with ctx.typing():
            count: int = 0
            minute: int = 0
            while count < len(everyone):
                since_zero = zero + datetime.timedelta(minutes=minute)
                count = len([e for e in everyone if e.infected_at <= since_zero])
                infected[minute] = count
                minute += 5

            chart = pygal.Line(show_legend=False)

            chart.title = _(ctx, "Infection spread")
            chart.width = 1200
            chart.height = 600

            chart.x_labels = infected.keys()
            chart.x_title = _(ctx, "Minutes since patient zero")
            chart.y_title = _(ctx, "# of infected")
            chart.interpolate = "cubic"
            chart._min = 0
            chart.add(_(ctx, "Infected"), infected.values())

            f = io.BytesIO()
            chart.render_to_png(f)
            f.seek(0)

        await ctx.reply(
            file=nextcord.File(fp=f, filename="Infection statistics.png"),
            mention_author=False,
        )
        f.close()

    @check.acl2(check.ACLevel.MOD)
    @infection_.command(name="infect")
    async def infection_infect(self, ctx, member: nextcord.Member):
        """Infect a member."""
        infected = Infected.add(
            member.id,
            guild_id=ctx.guild.id,
            channel_id=ctx.channel.id,
            message_id=ctx.message.id,
            infected_by=0,
        )
        if not infected:
            await ctx.reply(_(ctx, "That member cannot be infected."))
            return

        await ctx.reply(_(ctx, "Member infected."))
        await guild_log.info(
            ctx.author,
            ctx.channel,
            f"Infected member {member.name} as patient zero.",
        )

    @check.acl2(check.ACLevel.MOD)
    @infection_.group(name="config")
    async def infection_config_(self, ctx):
        """Manage infection."""
        await utils.discord.send_help(ctx)

    @check.acl2(check.ACLevel.MOD)
    @infection_config_.command(name="init")
    async def infection_config_init(self, ctx, role: nextcord.Role):
        """Initiate the infections."""
        config = InfectionConfig.add(guild_id=ctx.guild.id, role_id=role.id)
        if not config:
            await ctx.reply(_(ctx, "Config is already initiated."))
            return

        self.guilds = InfectionConfig.get_guild_ids()
        await ctx.reply(_(ctx, "Infection configuration has been initiated."))
        await guild_log.info(
            ctx.author.id,
            ctx.channel.id,
            f"Infection initiated for role {role}.",
        )

    @check.acl2(check.ACLevel.MOD)
    @infection_config_.command(name="enable")
    async def infection_config_enable(self, ctx):
        """Enable the spread of infection."""
        config = InfectionConfig.get(ctx.guild.id)
        if not config:
            await ctx.reply(_(ctx, "Config is already initiated."))
            return
        if config.enabled:
            await ctx.reply(_(ctx, "The virus is already spreadng."))
            return
        config.enabled = True
        config.save()

        await ctx.reply(_(ctx, "The virus will be spreadng now."))
        await guild_log.info(
            ctx.author,
            ctx.channel,
            "Infection spreading enabled.",
        )

    @check.acl2(check.ACLevel.MOD)
    @infection_config_.command(name="disable")
    async def infection_config_disable(self, ctx):
        """Disable the spread of infection."""
        config = InfectionConfig.get(ctx.guild.id)
        if not config:
            await ctx.reply(_(ctx, "Config is already initiated."))
            return
        if not config.enabled:
            await ctx.reply(_(ctx, "The virus is not spreadng."))
            return
        config.enabled = False
        config.save()

        await ctx.reply(_(ctx, "The virus will not be spreadng now."))
        await guild_log.info(
            ctx.author,
            ctx.channel,
            "Infection spreading disabled.",
        )

    @check.acl2(check.ACLevel.MOD)
    @infection_config_.command(name="quiet")
    async def infection_config_quiet(self, ctx):
        """Make the infection spread quiet by not assigning roles."""
        config = InfectionConfig.get(ctx.guild.id)
        if not config:
            await ctx.reply(_(ctx, "Config is already initiated."))
            return
        if config.quiet:
            await ctx.reply(_(ctx, "The spreading is already quiet."))
            return
        config.quiet = True
        config.save()

        await ctx.reply(_(ctx, "The virus will be spreadng quietly now."))
        await guild_log.info(
            ctx.author,
            ctx.channel,
            "Infection will be spreading quietly.",
        )

    @check.acl2(check.ACLevel.MOD)
    @infection_config_.command(name="verbose")
    async def infection_config_verbose(self, ctx):
        """Make the infection spread verbose by assigning roles."""
        config = InfectionConfig.get(ctx.guild.id)
        if not config:
            await ctx.reply(_(ctx, "Config is already initiated."))
            return
        if config.quiet:
            await ctx.reply(_(ctx, "The spreading is not quiet."))
            return
        config.quiet = False
        config.save()

        await ctx.reply(_(ctx, "The virus will be spreadng visibly now."))
        await guild_log.info(
            ctx.author,
            ctx.channel,
            "Infection will be spreading visibly.",
        )

    @check.acl2(check.ACLevel.MOD)
    @infection_config_.command(name="get")
    async def infection_config_get(self, ctx):
        """Display infection configuration."""
        config = InfectionConfig.get(ctx.guild.id)
        if not config:
            await ctx.reply(_(ctx, "Config not initiated."))
            return

        embed = utils.discord.create_embed(
            author=ctx.author,
            title=_(ctx, "Infection configuration"),
        )
        role: Optional[nextcord.Role] = ctx.guild.get_role(config.role_id)
        embed.add_field(
            name=_(ctx, "Role"),
            value=f"{role.name} ({role.id})" if role else _(ctx, "None"),
            inline=False,
        )
        embed.add_field(
            name=_(ctx, "Probability"),
            value=config.probability,
            inline=False,
        )
        embed.add_field(
            name=_(ctx, "Symptom delay"),
            value=f"{config.symptom_delay!s}",
            inline=False,
        )
        embed.add_field(
            name=_(ctx, "Cure delay"),
            value=f"{config.cure_delay!s}",
            inline=False,
        )
        embed.add_field(
            name=_(ctx, "Quiet"),
            value=_(ctx, "Yes") if config.quiet else _(ctx, "No"),
            inline=False,
        )
        embed.add_field(
            name=_(ctx, "Enabled"),
            value=_(ctx, "Yes") if config.enabled else _(ctx, "No"),
            inline=False,
        )
        await ctx.reply(embed=embed)

    @check.acl2(check.ACLevel.MOD)
    @infection_config_.command(name="probability")
    async def infection_config_probability(self, ctx, probability: float):
        """Set infection probability from interval <0, 1>."""
        config = InfectionConfig.get(ctx.guild.id)
        if not config:
            await ctx.reply(_(ctx, "Config not initiated."))
            return

        if probability < 0.0 or probability > 1.0:
            await ctx.reply(_(ctx, "Probability has to be in interval **<0, 1>**."))
            return

        config.probability = probability
        config.save()
        await ctx.reply(
            _(ctx, "Infection probability set to {probability}.").format(
                probability=probability
            )
        )

        await guild_log.info(
            ctx.author.id,
            ctx.channel.id,
            f"Infection spreading probability set to {probability}.",
        )

    #

    @commands.Cog.listener()
    async def on_message(self, message: nextcord.Message):
        if message.guild is None:
            return
        if message.author.bot:
            return
        if message.guild.id not in self.guilds:
            _trace(f"Guild {message.guild} not registered.")
            return
        config = InfectionConfig.get(message.guild.id)
        if not config or not config.enabled:
            _trace(f"Spreading is disabled in guild {message.guild}.")
            return

        previous_message = self.message_cache.get(message.channel, None)
        if not previous_message:
            _trace("Fetching previous message.")
            previous_messages = await message.channel.history(
                limit=1, before=message
            ).flatten()
            if previous_messages:
                previous_message = previous_messages[0]
            else:
                previous_message = None

        if not previous_message:
            _trace(f"No previous message before {message.id} in {message.channel}.")
            return

        self.message_cache[message.channel] = message

        if Infected.is_infected(message.guild.id, message.author.id):
            _trace(f"{message.author} is already infected.")
            return

        if not Infected.is_infected(message.guild.id, previous_message.author.id):
            _trace(f"Previous author {previous_message.author} not infected.")
            return

        roll: float = random.randint(0, 100) / 100
        probability: float = config.probability
        if roll > config.probability:
            _trace(f"Rolled {roll}, needed {probability} or less.")
            return

        _trace(f"Infecting {message.author}: rolled {roll} < {probability}.")
        Infected.add(
            message.author.id,
            guild_id=message.guild.id,
            channel_id=message.channel.id,
            message_id=message.id,
            infected_by=previous_message.author.id,
        )


def setup(bot) -> None:
    bot.add_cog(Infection(bot))
