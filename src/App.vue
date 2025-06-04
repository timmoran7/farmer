<script setup lang="ts">
import { ref } from "vue";
import type {
  PitchingStats,
  PlayerInfo,
  BoxScores,
  BattingResult,
  PitchingResult,
} from "@/models/statModels.ts";

const gameUrl = ref("");
const battingAll = ref<BattingResult[]>([]);
const pitchingAll = ref<PitchingResult[]>([]);

const validSoxTeams = [
  "cannon-ballers",
  "dash",
  "knights",
  "barons",
  "acl-white-sox",
  "dsl-white-sox",
];

let isHomeTeam = true;

const fetchBoxScoreData = async (url: string) => {
  const apiUri = convertGameUrlToApiUri(url);
  const response = await fetch(apiUri);
  const data = await response.json();
  const players = isHomeTeam
    ? data?.liveData?.boxscore?.teams?.home?.players || {}
    : data?.liveData?.boxscore?.teams?.away?.players || {};
  return extractBoxScores(players);
};

const extractBoxScores = (
  playerDataDict: Record<string, PlayerInfo>
): BoxScores => {
  function collectStatIfExists(
    obj: Record<string, any>,
    key: string,
    label: string,
    isPitching: boolean = false 
  ) {
    const count = obj[key] || 0;
    if(isPitching) {
      return count != 1 ? `${count} ${label}` : label;
    }
    else if (count > 0) {
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
        ["strikeOuts", "K"],
        ["stolenBases", "SB"],
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

const convertGameUrlToApiUri = (url: string): string => {
  const match = url.match(
    /^https:\/\/www\.milb\.com\/gameday\/([a-z0-9-]+)-vs-([a-z0-9-]+)\/\d{4}\/\d{2}\/\d{2}\/(\d+)\/final\/box$/i
  );
  if (match) {
    const [_, away, home, gameId] = match;
    if (validSoxTeams.includes(away)) {
      isHomeTeam = false;
    }

    return `https://ws.statsapi.mlb.com/api/v1.1/game/${gameId}/feed/live?language=en`;
  }
  throw new Error("Invalid game URL format");
};

const loadGame = async () => {
  const { battingResults, pitchingResults } = await fetchBoxScoreData(
    gameUrl.value
  );

  battingAll.value = battingResults;
  pitchingAll.value = pitchingResults;
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
        Generate Farm Report
      </button>
    </div>
    <div class="mt-4">
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
      Contact: timthemoran@gmail.com
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
}

footer {
  margin-bottom: 20px;
}
</style>
