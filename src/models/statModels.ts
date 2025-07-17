interface PlayerStats {
  batting?: BattingStats;
  pitching?: PitchingStats;
  
}

interface GameStatus {
  isSubstitute?: boolean;
}

interface Position {
  abbreviation?: string;
}

interface BattingStats {
  summary?: string;
  doubles?: number;
  triples?: number;
  homeRuns?: number;
  runs?: number;
  rbi?: number;
  baseOnBalls?: number;
  strikeOuts?: number;
}

export interface PitchingStats {
  inningsPitched: string;
  gamesStarted: string;
  wins: number;
  saves: number;
  hits: number;
  runs: number;
  earnedRuns: number;
  baseOnBalls: number;
  strikeOuts: number;
  pitchesThrown: number;
  strikes: number;
}

export interface PlayerInfo {
  stats?: PlayerStats;
  person?: {
    fullName?: string;
  };
  battingOrder?: string;
  gameStatus?: GameStatus;
  position?: Position;
}

export interface BattingResult {
  name: string;
  summary: string;
  sort_order: number;
}

export interface PitchingResult {
  name: string;
  summary: string;
  output: string;
  sort_order: string;
}

export interface BoxScore {
  battingResults: BattingResult[];
  pitchingResults: PitchingResult[];
}

export interface ReportResult {
  recordLine: string;
  boxScore: BoxScore;
  scoreLine: string;
  level: number;
  boxScoreLink: string;
  teamGameNum: number;
  formattedDate: string;
  nextDayRecordLine: string;
}