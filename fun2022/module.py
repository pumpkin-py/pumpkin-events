import aiohttp
from io import BytesIO
from pathlib import Path
from PIL import Image
from typing import List, Union

import nextcord
from nextcord.ext import commands

from pie import check, exceptions, i18n

try:
    from modules.fun.fun.module import Fun as SourceFun
    from modules.fun.fun.image_utils import ImageUtils
    from modules.fun.fun.database import Relation
except Exception:
    raise exceptions.ModuleException("events", "fun", "Missing dependence fun.fun.")

_ = i18n.Translator("modules/events").translate

DATA_DIR = Path(__file__).parents[2] / "fun/fun/data"
DATA_DIR2 = Path(__file__).parent / "data/"


class Fun2022(SourceFun):
    @commands.guild_only()
    @commands.cooldown(rate=3, per=30.0, type=commands.BucketType.user)
    @check.acl2(check.ACLevel.MEMBER)
    @commands.command()
    async def slap(self, ctx, *, user: Union[nextcord.Member, nextcord.Role] = None):
        """Slap someone"""
        if not await self._is_user_in_channel(ctx, user):
            await ctx.reply(_(ctx, "You can't do that, they are not in this channel."))
            return

        if user is None:
            source = self.bot.user
            target = ctx.author
        else:
            source = ctx.author
            target = user

        if type(target) == nextcord.Role:
            Relation.add(ctx.guild.id, source.id, None, "slap")
        else:
            Relation.add(ctx.guild.id, source.id, target.id, "slap")

        async with ctx.typing():
            url = target.display_avatar.replace(size=256).url
            async with aiohttp.ClientSession() as session:
                response: aiohttp.ClientResponse = await session.get(url)
                content: BytesIO = BytesIO(await response.read())
                avatar: Image = Image.open(content).convert("RGBA")

                frames = self.get_slap_frames(avatar)

                with BytesIO() as image_binary:
                    frames[0].save(
                        image_binary,
                        format="GIF",
                        save_all=True,
                        append_images=frames[1:],
                        duration=70,
                        loop=0,
                        transparency=0,
                        disposal=2,
                        optimize=False,
                    )
                    image_binary.seek(0)
                    await ctx.reply(
                        file=nextcord.File(fp=image_binary, filename="slap.gif"),
                        mention_author=False,
                    )

    @staticmethod
    def get_lick_frames(avatar: Image.Image) -> List[Image.Image]:
        """Get frames for the lick"""
        frames = []
        width, height = 605, 480
        voffset = (1, 0, 0, 1)
        hoffset = (0, 1, 1, 0)

        pepe = Image.open(DATA_DIR2 / "pepe_lick.png")
        avatar = ImageUtils.round_image(avatar.resize((130, 140)))

        for i in range(4):
            img = ("01", "02", "03", "02")[i]
            peepo = Image.open(DATA_DIR / f"lick/{img}.png")

            frame = Image.new("RGBA", (width, height), (54, 57, 63, 1))
            frame.paste(peepo, (0, 140), peepo)
            frame.paste(pepe, (50 + hoffset[i], 0), pepe)
            frame.paste(avatar, (425 + hoffset[i], voffset[i]), avatar)
            frames.append(frame)

        return frames

    @staticmethod
    def get_hyperlick_frames(avatar: Image.Image) -> List[Image.Image]:
        """Get frames for the hyperlick"""
        frames = []
        width, height = 605, 400
        voffset = (1, 0, 0, 1)
        hoffset = (0, 1, 1, 0)

        pepe = Image.open(DATA_DIR2 / "pepe_hyperlick.png")
        avatar = ImageUtils.round_image(avatar.resize((128, 140)))

        for i in range(4):
            img = ("01", "02", "03", "02")[i]
            peepo = Image.open(DATA_DIR / f"lick/{img}.png")

            frame = Image.new("RGBA", (width, height), (54, 57, 63, 1))
            frame.paste(peepo, (0, 40), peepo)
            frame.paste(pepe, (80 + hoffset[i], 0), pepe)
            frame.paste(avatar, (438 + hoffset[i], voffset[i]), avatar)
            frames.append(frame)

        return frames

    @staticmethod
    def get_slap_frames(avatar: Image.Image) -> List[Image.Image]:
        """Get frames for the slap"""
        frames = []
        width, height = 190, 260
        hoffset = (20, 17, 18, 21, 18, 24, 33, 38)
        voffset = (45, 46, 45, 43, 32, 18, 7, 3)

        avatar = ImageUtils.round_image(avatar.resize((45, 45)))

        for i in range(8):
            frame_object = Image.open(DATA_DIR2 / f"slap/0{i+1}.png")

            frame = Image.new("RGBA", (width, height), (54, 57, 63, 1))
            frame.paste(frame_object, (0, 0), frame_object)
            frame.paste(avatar, (voffset[i], hoffset[i]), avatar)
            frames.append(frame)

        return frames


def setup(bot):
    bot.add_cog(Fun2022(bot))
