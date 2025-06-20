<script setup lang="ts">
import { ref } from "vue";
import type {
  PitchingStats,
  PlayerInfo,
  BoxScore,
  BattingResult,
  PitchingResult,
  ReportResult,
} from "@/models/statModels.ts";

const gameUrl = ref("");
const battingAll = ref<BattingResult[]>([]);
const pitchingAll = ref<PitchingResult[]>([]);
const reportResults = [] as ReportResult[];

const isFullReport = ref(false);

const validSoxTeams: { [key: string]: number } = {
  knights: 1,
  barons: 2,
  dash: 3,
  "cannon ballers": 4,
  "acl white sox": 5,
  "dsl white sox": 6,
};
const validSoxTeamSlugs = [
  "cannon-ballers",
  "dash",
  "knights",
  "barons",
  "acl-white-sox",
  "dsl-white-sox",
];

const getMostRecentCompletedDate = () => {
  const now = new Date();

  // Convert to US Central Time (America/Chicago)
  const centralNow = new Date(
    now.toLocaleString("en-US", { timeZone: "America/Chicago" })
  );

  const cutoffHour = 18; // 6 PM

  const targetDate = new Date(centralNow);
  if (centralNow.getHours() < cutoffHour) {
    // Before 6 PM — use yesterday
    targetDate.setDate(targetDate.getDate() - 1);
  }

  const year = targetDate.getFullYear();
  const month = String(targetDate.getMonth() + 1).padStart(2, "0"); // Months are 0-based
  const day = String(targetDate.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
};

const convertGameUrlToApiUri = (
  url: string,
  gameId: string = ""
): [string, boolean] => {
  let isHomeTeam = true;

  const match = url.match(
    /^https:\/\/www\.milb\.com\/gameday\/([a-z0-9-]+)-vs-([a-z0-9-]+)\/\d{4}\/\d{2}\/\d{2}\/(\d+)\/final\/box$/i
  );
  if (match) {
    const [_, away, home, gameId] = match;
    if (validSoxTeamSlugs.includes(away)) {
      isHomeTeam = false;
    }

    let apiUri = `https://ws.statsapi.mlb.com/api/v1.1/game/${gameId}/feed/live?language=en`;
    return [apiUri, isHomeTeam];
  }
  throw new Error("Invalid game URL format");
};

const extractFullReport = async () => {
  const mostRecentDateString = getMostRecentCompletedDate();
  const mostRecentSlashDate = mostRecentDateString.replace(/-/g, "/");

  const allSoxBoxResponse = await fetch(
    `https://bdfed.stitch.mlbinfra.com/bdfed/transform-milb-scoreboard?stitch_env=prod&sortTemplate=4&sportId=11&&sportId=12&&sportId=13&&sportId=14&&sportId=16&startDate=${mostRecentDateString}&endDate=${mostRecentDateString}&gameType=R&&gameType=F&&gameType=D&&gameType=L&&gameType=W&&gameType=A&&gameType=C&season=2025&language=en&leagueId=&contextTeamId=milb&teamId=580&&teamId=633&&teamId=247&&teamId=1997&&teamId=487&&teamId=494&orgId=145`
  );
  const allBoxData = await allSoxBoxResponse.json();

  for (const game of allBoxData?.dates[0]?.games || []) {
    const isCancelled = game.status.codedGameState === "C";
    if (isCancelled) {
      continue;
    }

    const gameId = game.gamePk;
    const awayTeam = game.teams.away;
    const homeTeam = game.teams.home;

    const [awayName, awayFullName, awayLevel, awayRecord, awayScore] = [
      awayTeam.team.teamName,
      awayTeam.team.name,
      awayTeam.team.sport.name,
      awayTeam.leagueRecord,
      awayTeam.score,
    ];
    const awayRecordString = `${awayRecord.wins}-${awayRecord.losses}`;

    const [homeName, homeFullName, homeLevel, homeRecord, homeScore] = [
      homeTeam.team.teamName,
      homeTeam.team.name,
      homeTeam.team.sport.name,
      homeTeam.leagueRecord,
      homeTeam.score,
    ];
    const homeRecordString = `${homeRecord.wins}-${homeRecord.losses}`;

    const isHome = !Object.keys(validSoxTeams).includes(awayName.toLowerCase());

    const scoreLine = `FINAL: ${awayFullName} ${awayScore}, ${homeFullName} ${homeScore} |`;
    let recordLine = isHome
      ? `${homeLevel} ${homeFullName} (${homeRecordString})`
      : `${awayLevel} ${awayFullName} (${awayRecordString})`;
    if (recordLine.startsWith("Rookie ")) {
      recordLine = recordLine.replace("Rookie ", "");
    }
    const level = isHome
      ? validSoxTeams[homeName.toLowerCase()]
      : validSoxTeams[awayName.toLowerCase()];

    const apiUri = `https://ws.statsapi.mlb.com/api/v1.1/game/${gameId}/feed/live?language=en`;
    const boxScoreLink = `https://www.milb.com/gameday/${awayName.toLowerCase().replaceAll(" ", "-")}-vs-${homeName.toLowerCase().replaceAll(" ", "-")}/${mostRecentSlashDate}/${gameId}/final/box`;

    const boxScore = await fetchBoxScoreData("", apiUri, isHome);
    const reportResult: ReportResult = {
      recordLine,
      boxScore,
      scoreLine,
      level,
      boxScoreLink,
    };
    reportResults.push(reportResult);
  }
  reportResults.sort((a, b) => {
    return a.level - b.level; // Sort by level first
  });
};

const fetchBoxScoreData = async (
  url: string,
  reportApiUri: string = "",
  reportIsHome: boolean = false
) => {
  let apiUri: string = "";
  let isHomeTeam: boolean = false;

  if (reportApiUri) {
    apiUri = reportApiUri;
    isHomeTeam = reportIsHome;
  } else {
    [apiUri, isHomeTeam] = convertGameUrlToApiUri(url);
  }

  const response = await fetch(apiUri);
  const data = await response.json();
  const players = isHomeTeam
    ? data?.liveData?.boxscore?.teams?.home?.players || {}
    : data?.liveData?.boxscore?.teams?.away?.players || {};

  return extractBoxScore(players);
};

const extractBoxScore = (
  playerDataDict: Record<string, PlayerInfo>
): BoxScore => {
  function collectStatIfExists(
    obj: Record<string, any>,
    key: string,
    label: string,
    isPitching: boolean = false
  ) {
    const count = obj[key] || 0;
    if (isPitching) {
      return count != 1 ? `${count} ${label}` : label;
    } else if (count > 0) {
      return count > 1 ? `${count} ${label}` : label;
    }
    return null;
  }

  const battingResults = [];
  const pitchingResults = [];

  for (const playerId in playerDataDict) {
    const playerInfo = playerDataDict[playerId];
    const gameStatus = playerInfo?.gameStatus || {};
    const position = playerInfo?.position?.abbreviation || {};
    const stats = playerInfo?.stats || {};
    const batting = stats?.batting || {};

    const pitching: PitchingStats = stats?.pitching || {
      inningsPitched: "0.0",
      gamesStarted: "0",
      wins: 0,
      saves: 0,
      hits: 0,
      runs: 0,
      earnedRuns: 0,
      baseOnBalls: 0,
      strikeOuts: 0,
      pitchesThrown: 0,
      strikes: 0,
    };
    const name = playerInfo?.person?.fullName || "Unknown";
    const isPinchHitter = gameStatus?.isSubstitute || false;

    if (Object.keys(batting).length > 0) {
      const battingOrder = isPinchHitter ? "" : playerInfo.battingOrder || "";
      const sortOrder = battingOrder ? parseInt(battingOrder[0]) : 10;

      const rawSummary = batting.summary || "";
      const [hits = "0", atBatsPlus = "0"] = rawSummary.split("-");
      let summary = `${name} (${position}): ${hits}-for-${atBatsPlus[0]}`;

      const extras = [];
      let numHomers = 0;

      for (const [key, label] of [
        ["doubles", "2B"],
        ["triples", "3B"],
        ["homeRuns", "HR"],
        ["runs", "R"],
        ["rbi", "RBI"],
        ["baseOnBalls", "BB"],
        ["stolenBases", "SB"],
        ["strikeOuts", "K"],
      ]) {
        const stat = collectStatIfExists(batting, key, label);
        if (stat) {
          if (key === "homeRuns") numHomers = parseInt(stat[0]);
          if (
            (key === "runs" || key === "rbi") &&
            parseInt(stat[0]) === numHomers
          )
            continue;
          extras.push(stat);
        }
      }

      if (extras.length > 0) summary += `, ${extras.join(", ")}`;

      battingResults.push({ name, summary, sort_order: sortOrder });
    } else if (Object.keys(pitching).length > 0) {
      let position = pitching.gamesStarted == "1" ? "SP" : "RP";
      let wins = pitching.wins || 0;
      let saves = pitching.saves || 0;
      let summary = `${name} (${position}): ${pitching.inningsPitched || "0.0"} IP`;
      const extras = [];

      const earnedRuns = pitching.earnedRuns || 0;

      for (const [key, label] of [
        ["hits", "H"],
        ["runs", "R"],
        ["earnedRuns", "ER"],
        ["baseOnBalls", "BB"],
        ["strikeOuts", "K"],
      ]) {
        const count = pitching[key as keyof PitchingStats] || 0;
        const stat = collectStatIfExists(pitching, key, label, true);
        if (key === "earnedRuns" && count === 0) continue;
        if (key === "runs" && count === earnedRuns && count != 0) continue;
        extras.push(stat);
      }

      if (extras.length > 0) summary += `, ${extras.join(", ")}`;
      if (wins > 0) {
        summary += ` (WIN)`;
      }
      if (saves > 0) {
        summary += ` (SAVE)`;
      }

      const output = `${pitching.pitchesThrown} pitches, ${pitching.strikes} strikes`;

      const sort_order = position;
      pitchingResults.push({
        name,
        summary,
        output,
        sort_order,
      });
    }
  }

  battingResults.sort((a, b) => a.sort_order - b.sort_order);
  pitchingResults.sort((a, b) => b.sort_order.localeCompare(a.sort_order));

  return { battingResults, pitchingResults };
};

const loadGame = async () => {
  const { battingResults, pitchingResults } = await fetchBoxScoreData(
    gameUrl.value
  );

  battingAll.value = battingResults;
  pitchingAll.value = pitchingResults;

  isFullReport.value = false;
};

const loadAllGames = async () => {
  await extractFullReport();
  isFullReport.value = true;
};
</script>

<template>
  <div class="container mt-5">
    <div class="text-center entry">
      <input
        class="form-control w-auto"
        placeholder="Game Box URL"
        type="text"
        v-model="gameUrl"
      />
      <button
        type="button"
        class="btn btn-secondary d-inline mx-3"
        @click="loadGame"
      >
        Generate Box Score
      </button>
    </div>
    <div class="text-center entry">
      <button
        type="button"
        class="btn btn-primary d-inline mx-3"
        @click="loadAllGames"
      >
        Generate Full Report
      </button>
    </div>
    <div v-if="isFullReport">
      <div v-for="result in reportResults" class="mt-4">
        <h3>{{ result.recordLine }}</h3>
        <ul>
          <li
            v-for="batter in result.boxScore.battingResults"
            :key="batter.name"
          >
            {{ batter.summary }}
          </li>
          <li
            v-for="pitcher in result.boxScore.pitchingResults"
            :key="pitcher.name"
          >
            {{ pitcher.summary }}
            <ul>
              <li>{{ pitcher.output }}</li>
            </ul>
          </li>
        </ul>
        <span
          ><h3>{{ result.scoreLine }}</h3>
          &nbsp;<a :href="result.boxScoreLink" target="_blank"
            ><h3>Box Score</h3></a
          ></span
        >
      </div>
    </div>
    <div class="mt-4" v-else>
      <ul>
        <li v-for="batter in battingAll" :key="batter.name">
          {{ batter.summary }}
        </li>
        <li v-for="pitcher in pitchingAll" :key="pitcher.name">
          {{ pitcher.summary }}
          <ul>
            <li>{{ pitcher.output }}</li>
          </ul>
        </li>
      </ul>
    </div>

    <!-- Footer -->
    <footer class="text-center mt-5 text-muted">
      Generate Box Score: Generates a summary line for all batters and all
      pitchers, with pinch hitters being at the end of the batter list. Please
      remove lines as you see fit. Note: relievers are not in order of
      appearance.<br><br>Generate Full Report: Generates a full day's report with box
      scores in the format noted above, may need to copy/paste in chunks to get
      Wordpress to recognize the different sections.
    </footer>
  </div>
</template>

<style scoped>
body {
  background-color: #f8f9fa;
}
.container {
  margin-top: 30px;
}

.entry {
  display: flex;
  justify-content: center;
  margin-bottom: 15px;
}

span {
  display: flex;
}

a {
  text-decoration: none;
  color: #007bff;
}

footer {
  margin-bottom: 20px;
}
</style>
