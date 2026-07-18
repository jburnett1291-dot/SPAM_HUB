# ═══════════════════════════════════════════════════════════════════════════
#  /award card  —  post an award card image; bot pulls the winner's stats,
#  commits the image to SPAM_HUB/cards/, and records the stat line so the Hub
#  shows the player's real numbers under the card.
#
#  WHERE TO PASTE: anywhere AFTER your groups are added (e.g. right after the
#  `bot.tree.add_command(award_group)` line, ~line 3486). It relies on things
#  already defined above it: bot, award_group, load_data, player_autocomplete.
#
#  ONE-TIME SETUP: add this to your .env (same folder as the bot):
#      GITHUB_TOKEN=github_pat_xxxxxxxx
#  Make the token at github.com → Settings → Developer settings →
#  Fine-grained tokens → repo SPAM_HUB → Contents: Read and write.
# ═══════════════════════════════════════════════════════════════════════════

import base64  # noqa: E402  (safe even if already imported at the top of your bot)

GH_TOKEN  = os.environ.get("GITHUB_TOKEN", "")
GH_REPO   = os.environ.get("GITHUB_REPO", "jburnett1291-dot/SPAM_HUB")
GH_BRANCH = os.environ.get("GITHUB_BRANCH", "main")
GH_CARDS  = os.environ.get("CARDS_PATH", "cards")
GH_API    = "https://api.github.com"
_GH_OK_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif")


def _gh_headers():
    return {
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "QSPN-award-card",
    }


def _gh_slug(s):
    """Filename-safe, case preserved: 'DynastyOnTop' stays 'DynastyOnTop'."""
    return re.sub(r"[^A-Za-z0-9]+", "_", str(s or "")).strip("_") or "card"


async def _gh_fetch(session, path):
    """Return (sha, decoded_text) for a repo file, or (None, None) if missing."""
    url = f"{GH_API}/repos/{GH_REPO}/contents/{path}"
    async with session.get(url, params={"ref": GH_BRANCH}, headers=_gh_headers()) as r:
        if r.status == 200:
            d = await r.json()
            txt = None
            if d.get("content"):
                try:
                    txt = base64.b64decode(d["content"]).decode("utf-8")
                except Exception:
                    txt = None
            return d.get("sha"), txt
        return None, None


async def _gh_put(session, path, content_b64, message, sha=None):
    url = f"{GH_API}/repos/{GH_REPO}/contents/{path}"
    payload = {"message": message, "content": content_b64, "branch": GH_BRANCH}
    if sha:
        payload["sha"] = sha
    async with session.put(url, json=payload, headers=_gh_headers()) as r:
        try:
            body = await r.json()
        except Exception:
            body = {}
        return r.status, body


def _award_player_line(player, season=None):
    """Pull the winner's averages off the live sheet. Returns a dict or None."""
    try:
        p_df, _ = load_data()
    except Exception:
        return None
    if p_df is None or getattr(p_df, "empty", True):
        return None
    pp = p_df[p_df["PlayerName"].astype(str) == str(player)]
    if season:
        pp = pp[pd.to_numeric(pp["Season"], errors="coerce") == int(season)]
    if pp.empty:
        return None

    def m(c):
        return float(pd.to_numeric(pp[c], errors="coerce").mean()) if c in pp.columns else 0.0

    gp = int(pp["Game_ID"].nunique()) if "Game_ID" in pp.columns else len(pp)
    pts, reb, ast = m("PTS"), m("REB"), m("AST")
    stl, blk, tpm = m("STL"), m("BLK"), m("3PM")
    team = ""
    if "TeamName" in pp.columns and pp["TeamName"].notna().any():
        team = str(pp["TeamName"].dropna().iloc[-1])
    ext = (f"{pts:.1f} PPG \u2022 {reb:.1f} RPG \u2022 {ast:.1f} APG "
           f"\u2022 {(stl + blk):.1f} STK \u2022 {tpm:.1f} 3PM")
    return {"gp": gp, "team": team, "pts": pts, "reb": reb, "ast": ast,
            "stl": stl, "blk": blk, "tpm": tpm, "stats": ext}


@award_group.command(name="card",
                     description="Post an award card — bot pulls the winner's stats & adds it to the Hub")
@app_commands.describe(
    image="The award card image (PNG / JPG / WEBP)",
    award="Award or label, e.g. MVP, OPOY, DPOY",
    player="Winner — start typing to pick from the sheet",
    season="Season number (optional — leave blank for career averages)",
    overwrite="Replace if a card with the same name already exists",
)
@app_commands.autocomplete(player=player_autocomplete)
async def award_card(interaction: discord.Interaction,
                     image: discord.Attachment,
                     award: str,
                     player: str,
                     season: int = None,
                     overwrite: bool = False):
    await interaction.response.defer(thinking=True)

    if not GH_TOKEN:
        return await interaction.followup.send(
            "❌ No `GITHUB_TOKEN` in the bot's .env. Add it and restart.")
    if not (image.content_type or "").startswith("image/"):
        return await interaction.followup.send("❌ That attachment isn't an image.")

    # --- match the winner to their real stats ---
    line = _award_player_line(player, season)
    if line is None:
        return await interaction.followup.send(
            f"⚠️ Couldn't find stats for **{player}**"
            + (f" in Season {season}" if season else "")
            + ". Check the name (use the autocomplete) or the season.")

    # --- clean, matchable filename: award_player[_sN].ext ---
    ext = os.path.splitext(image.filename)[1].lower()
    if ext not in _GH_OK_EXT:
        ext = ".png"
    stem = f"{_gh_slug(award)}_{_gh_slug(player)}" + (f"_s{season}" if season else "")
    path = f"{GH_CARDS}/{stem}{ext}"

    raw = await image.read()
    content_b64 = base64.b64encode(raw).decode("utf-8")

    async with aiohttp.ClientSession() as session:
        sha, _ = await _gh_fetch(session, path)
        if sha and not overwrite:
            return await interaction.followup.send(
                f"⚠️ `{stem}{ext}` already exists. Re-run with **overwrite: True** to replace it.")

        msg = f"Add card: {award} - {player}" + (f" (S{season})" if season else "")
        status, body = await _gh_put(session, path, content_b64, msg, sha=sha)
        if status not in (200, 201):
            detail = body.get("message", body) if isinstance(body, dict) else body
            return await interaction.followup.send(
                f"❌ GitHub rejected the image ({status}): {detail}")

        # --- record stats in cards/meta.json so the Hub shows the line ---
        try:
            meta_path = f"{GH_CARDS}/meta.json"
            msha, mtext = await _gh_fetch(session, meta_path)
            meta = {}
            if mtext:
                try:
                    meta = json.loads(mtext)
                except Exception:
                    meta = {}
            meta[stem] = {"award": award, "player": player,
                          "team": line["team"], "season": season,
                          "stats": line["stats"]}
            mb64 = base64.b64encode(json.dumps(meta, indent=2).encode("utf-8")).decode("utf-8")
            await _gh_put(session, meta_path, mb64, f"meta: {award} - {player}", sha=msha)
        except Exception:
            pass  # image already committed; metadata is best-effort

    emb = discord.Embed(
        title="🏅 Card added to the Hub",
        description=(f"**{award} — {player}**" + (f"  •  S{season}" if season else "")
                     + (f"\n{line['team']}" if line["team"] else "")
                     + f"\n`{path}`"),
        color=0xD4AF37)
    emb.add_field(name="Matched stats", value=line["stats"], inline=False)
    emb.add_field(name="Games", value=str(line["gp"]), inline=True)
    emb.set_image(url=image.url)
    emb.set_footer(text="Appears on Awards & Rewards within ~1 min (auto-scan).")
    await interaction.followup.send(embed=emb)
