import requests # type: ignore
import time
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def extract_box_scores(player_data_dict):
    def collect_stat_if_exists(obj, key, label):
        count = obj.get(key, 0)
        if count > 0:
            return f"{count} {label}" if count > 1 else label
        return None

    battingResults = []
    pitchingResults = []

    for player_id, player_info in player_data_dict.items():
        stats = player_info.get("stats", {})
        batting = stats.get("batting", {})
        pitching = stats.get("pitching", {})
        name = player_info["person"]["fullName"]

        if batting:
            batting_order = player_info.get("battingOrder", "")
            sort_order = int(batting_order[0]) if batting_order else 9  # default to end if missing
            
            raw_summary = batting.get("summary", "")  # e.g. "1-4"
            hits, at_bats_plus_rest = raw_summary.split("-") if "-" in raw_summary else ("0", "0")
            summary = f"{hits}-for-{at_bats_plus_rest[0]}"
            
            extras = []
            numHomers = 0
            for stat_key, label in [
                ("doubles", "2B"),
                ("triples", "3B"),
                ("homeRuns", "HR"),
                ("runs", "R"),
                ("rbi", "RBI"),
                ("baseOnBalls", "BB"),
                ("strikeOuts", "K"),
            ]:
                stat = collect_stat_if_exists(batting, stat_key, label)
                if stat:
                    #remove redundancies with homers
                    if stat_key == "homeRuns":
                        numHomers = stat[0]
                    if stat_key == "runs" or stat_key == "rbi" and stat[0] == numHomers:
                        continue
                    extras.append(stat)

            if extras:
                summary += ", " + ", ".join(extras)

            result = {
                "name": name,
                "summary": summary,
                "sort_order": sort_order
            }
            battingResults.append(result)
        elif pitching:
            ip = pitching.get("inningsPitched", "0.0")
            summary = f"{ip} IP"
            extras = []

            numEarnedRuns = pitching.get("earnedRuns", 0)
            for key, label in [
                ("hits", "H"),
                ("runs", "R"),
                ("earnedRuns", "ER"),
                ("baseOnBalls", "BB"),
                ("strikeOuts", "K"),
            ]:
                count = pitching.get(key, 0)
                stat = f"{count} {label}"
                if stat:
                    if key == "runs" and count == numEarnedRuns:
                        continue
                    extras.append(stat)

            if extras:
                summary += ", " + ", ".join(extras)

            result = {
                "name": name,
                "summary": summary,
                "pitches": pitching.get("pitchesThrown", 0),
                "strikes": pitching.get("strikes", 0)
            }
            pitchingResults.append(result)

    # Sort by lineup position
    battingResults.sort(key=lambda x: x["sort_order"])

    # Remove sort_order from final output
    for r in battingResults:
        del r["sort_order"]

    return (battingResults, pitchingResults)

# Scraper function
def scrape(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'}
    response = requests.get(url, headers=headers, verify=False)
    time.sleep(0.5)
    data = response.json()

    awayBox = data['liveData']['boxscore']['teams']['away']['players']
    (battingResults, pitchingResults) = extract_box_scores(awayBox)

    player = 1
    print(battingResults[player]['name'])
    print(battingResults[player]['summary'])

    pitcher = 4
    print(pitchingResults[pitcher]['name'])
    print(pitchingResults[pitcher]['summary'])
    print(pitchingResults[pitcher]['pitches'])
    print(pitchingResults[pitcher]['strikes'])

if __name__ == '__main__':
    scrape("https://ws.statsapi.mlb.com/api/v1.1/game/786716/feed/live?language=en")