import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import pytz
from datetime import datetime
from event_logic import get_weather_recommendations, get_todays_events, get_going_out_events
from weather import get_weather, needs_umbrella
from google_auth import get_calendar_service
import os

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True  # Required so your bot can read messages

bot = commands.Bot(command_prefix="!", intents=intents)

service = get_calendar_service()


def format_weather(weather, umbrella):
    return (
        f"{weather['emoji']} {weather['description']}\n"
        f"🌡️ Event range: {weather['min_temp']:.1f}°C–{weather['max_temp']:.1f}°C\n"
        f"🧥 Feels like: {weather['min_feels_like']:.1f}°C–"
        f"{weather['max_feels_like']:.1f}°C\n"
        f"🌧️ Rain chance: {weather['rain_chance']:.0f}%\n"
        f"💨 Wind: up to {weather['wind_speed']:.0f} km/h\n"
        + ("→ Bring an umbrella.\n" if umbrella else "→ No umbrella needed.\n")
    )

@tasks.loop(minutes=1)
async def daily_check():
    tz = pytz.timezone("Australia/Sydney")
    now = datetime.now(tz)

    # Run at 7:00 AM Sydney time
    if now.hour == 7 and now.minute == 0:
        channel = bot.get_channel(1463507490720448678)

        events = get_going_out_events(service)
        if not events:
            return

        recs = get_weather_recommendations(events)

        message = f"<@{467970434235891712}> **Today's Going-Out Weather Summary:**\n\n"
        for r in recs:
            event = r["event"]
            weather = r["weather"]

            summary = event["summary"]
            start_str = event["start"].get("dateTime")
            if start_str:
                start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                start_label = start.astimezone(tz).strftime("%I:%M %p")
            else:
                start_label = "All day"

            message += f"- **{summary}** at **{start_label}**\n"
            if weather is None:
                message += "⚠️ Event-time forecast unavailable.\n\n"
            else:
                message += format_weather(weather, r["umbrella"]) + "\n"

        await channel.send(message)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

    if not daily_check.is_running():
        daily_check.start()

@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

@bot.command()
async def weather(ctx):
    # Sydney coordinates
    lat = -33.8688
    lon = 151.2093

    report = get_weather(lat, lon)
    await ctx.send(
        "**Weather for the next two hours:**\n"
        + format_weather(report, needs_umbrella(report))
    )

@bot.tree.command(name="events", description="Show today's calendar events")
async def events(interaction: discord.Interaction):
    await interaction.response.defer()

    events = get_todays_events(service)

    if not events:
        await interaction.followup.send("No events scheduled for today.")
        return

    message = "**Today's Going-Out Events:**\n"
    for event in events:
        start_str = event["start"].get("dateTime")

        if start_str:
            dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            sydney = pytz.timezone("Australia/Sydney")
            local_dt = dt.astimezone(sydney)

            # Choose your preferred format:
            time_24h = local_dt.strftime("%H:%M")
            time_ampm = local_dt.strftime("%I:%M %p")

            message += f"- **{event['summary']}** at `{time_24h}` **({time_ampm})**\n"
        else:
            message += f"- **{event['summary']}** (All day)\n"

    await interaction.followup.send(message)

@bot.tree.command(name="goingout", description="Show today's going-out events")
async def going_out(interaction: discord.Interaction):
    await interaction.response.defer()

    events = get_going_out_events(service)

    if not events:
        await interaction.followup.send("No going-out events today.")
        return

    message = "**Today's Going-Out Events:**\n"
    for event in events:
        start_str = event["start"].get("dateTime")

        if start_str:
            dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            sydney = pytz.timezone("Australia/Sydney")
            local_dt = dt.astimezone(sydney)

            # Choose your preferred format:
            time_24h = local_dt.strftime("%H:%M")
            time_ampm = local_dt.strftime("%I:%M %p")

            message += f"- **{event['summary']}** at `{time_24h}` **({time_ampm})**\n"
        else:
            message += f"- **{event['summary']}** (All day)\n"


    await interaction.followup.send(message)

bot.run(os.getenv("DISCORD_TOKEN"))
