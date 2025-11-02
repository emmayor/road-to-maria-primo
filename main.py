import discord
import os
import asyncio
import base64
import hashlib
import aiohttp

from dotenv import load_dotenv
from discord.ext import commands, tasks

# Create bot with intents
intents = discord.Intents.all()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix="/", intents=intents)

# Load environment variables
load_dotenv()
discord_token = os.getenv("DISCORD_TOKEN")
iracing_email = os.getenv("IRACING_EMAIL")
iracing_password = os.getenv("IRACING_PASSWORD")
high_speed_racism_id = os.getenv("DISCORD_HSP_CHANNEL_ID")

# Response variables
iracing_auth_data = None
iracing_user_data = None

# cust_ids
cust_ids = ["1136936", "1211220", "656021", "895659"]

# http
iracing_url = "https://members-ng.iracing.com"
headers = {"User-Agent": "RoadToMariaPrimo/1.0 (+https://tbq.com)"}


def encode_pw(username, password):
    initialHash = hashlib.sha256((password + username.lower()).encode('utf-8')).digest()
    hashInBase64 = base64.b64encode(initialHash).decode('utf-8')
    return hashInBase64


# Create a single shared aiohttp session for your bot
session: aiohttp.ClientSession | None = None


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    # Command synchronization
    try:
        synced = await bot.tree.sync()
        print(f"🔁 Synced {len(synced)} commands")
    except Exception as e:
        print(f"Error syncing commands: {e}")
    # iRacing authentication
    try:
        iracing_auth_data = await authenticate(iracing_email, iracing_password)
        print(f"iRacing authentication successfull - {iracing_auth_data["email"]} - {iracing_auth_data["custId"]}")
        post_info.start()
    except Exception as e:
        print(f"Error while authenticating with iRacing: {e}")


@bot.tree.command(name="info", description="A CUANTO ESTAN LOS BONEKOS DE LA PRIMAAAA????")
async def info(interaction: discord.Interaction):
    embed = await build_info_embed()
    await interaction.response.send_message(embed=embed)


async def build_info_embed():
    reference_id = 895659
    data = await get_multiple_users_data(cust_ids)
    scores = {}
    ref_scores = {}

    for member in data.get("members", []):
        cust_id = member["cust_id"]
        name = member["display_name"]

        sports_car_score = None
        formula_car_score = None

        for lic in member.get("licenses", []):
            cat = lic["category_name"]
            if cat == "Sports Car":
                sports_car_score = lic.get("irating")
            elif cat == "Formula Car":
                formula_car_score = lic.get("irating")
        # store separately if reference user
        if cust_id == reference_id:
            ref_scores = {
                "Sports Car": sports_car_score,
                "Formula Car": formula_car_score
            }
        scores[name] = {
            "Sports Car": sports_car_score,
            "Formula Car": formula_car_score
        }

    # Sort players by category
    sports_sorted = sorted(
        [(name, data["Sports Car"]) for name, data in scores.items() if data["Sports Car"] is not None],
        key=lambda x: x[1],
        reverse=True
    )
    formula_sorted = sorted(
        [(name, data["Formula Car"]) for name, data in scores.items() if data["Formula Car"] is not None],
        key=lambda x: x[1],
        reverse=True
    )

    def make_leaderboard(data, category):
        ref_score = ref_scores.get(category)
        lines = []
        for name, score in data:
            if ref_score is None or score is None or ref_score == score:
                comparison = ""
            elif score > ref_score:
                comparison = "Bien ahí boneko, seguí así! Sos buenísimo! 💪"
            else:
                comparison = "Dejá de preocuparte por boludeces y aprendé a manejar. 🏎️"
            lines.append(f"**{name}** — {score} pts - {comparison}")
        return "\n".join(lines)

    embed = discord.Embed(
        title="🏁 A VER COMO ANDAN ESTOS BONEKOS",
        description="Racismo de Alta Velocidad",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="🏎️ Sports Car",
        value=make_leaderboard(sports_sorted, "Sports Car") if sports_sorted else "No hay datos disponibles",
        inline=False
    )

    embed.add_field(
        name="🏁 Formula Car",
        value=make_leaderboard(formula_sorted, "Formula Car") if formula_sorted else "No hay datos disponibles",
        inline=False
    )

    embed.set_footer(text="Powered by El Más Grande")
    return embed


@tasks.loop(minutes=60)
async def post_info():
    print(high_speed_racism_id)
    channel = await bot.fetch_channel(high_speed_racism_id)
    if not channel:
        print("⚠️ Channel not found. Check CHANNEL_ID.")
    embed = await build_info_embed()
    await channel.send(embed=embed)


async def authenticate(email, password):
    url = f"{iracing_url}/auth"
    payload = {
        "email": iracing_email,
        "password": encode_pw(iracing_email, iracing_password)
    }
    return await post(url, payload)


async def get_multiple_users_data(cust_ids):
    cust_ids_joint = ",".join(cust_ids)
    url = f"{iracing_url}/data/member/get?cust_ids={cust_ids_joint}&include_licenses=true"
    response = await get(url)
    return await get(response["link"])


async def get_user_data(cust_id):
    url = f"{iracing_url}/data/member/get?cust_ids={cust_id}&include_licenses=true"
    response = await get(url)
    return await get(response["link"])


async def get(url):
    global session
    if session is None or session.closed:
        # give a sensible User-Agent for APIs
        session = aiohttp.ClientSession(headers=headers)
    try:
        async with session.get(url, timeout=15) as resp:
            status = resp.status
            try:
                data = await resp.json()
                print("GET - ", status)
            except Exception:
                data = None
            if status == 200:
                return data
    except asyncio.TimeoutError:
        print("GET Timeout")
        return None
    except Exception as e:
        print("GET Error", e)
        return None


async def post(url, payload):
    global session
    if session is None or session.closed:
        # give a sensible User-Agent for APIs
        session = aiohttp.ClientSession(headers=headers)
    try:
        async with session.post(url, json=payload, timeout=15) as resp:
            status = resp.status
            try:
                data = await resp.json()
            except Exception:
                data = None
            if status == 200:
                return data
    except asyncio.TimeoutError:
        print("POST Timeout")
        return None
    except Exception as e:
        print("POST Error", e)
        return None

bot.run(discord_token)
