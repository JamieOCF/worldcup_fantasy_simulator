import math

import random

from typing import List

from models import Teams, Player

from collections import defaultdict





def _poisson(lam: float) -> int:

    L = math.exp(-lam)

    k = 0

    p = 1.0

    while True:

        k += 1

        p *= random.random()

        if p <= L:

            return k - 1





def _weighted_choice(items: List, weights: List[float]):

    total = sum(weights)

    if total <= 0:

        return random.choice(items)

    r = random.random() * total

    upto = 0.0

    for it, w in zip(items, weights):

        upto += w

        if r <= upto:

            return it

    return items[-1]





class Match:

    AVG_XG = 4.5



    def __init__(self, home: Teams, away: Teams, knockout: bool = False):

        self.home = home

        self.away = away

        self.knockout = knockout

        self.timeline: List[dict] = []

        self.score = {home.name: 0, away.name: 0}



    def _team_attack_value(self, team: Teams) -> float:

        fwd = team.players.get("Forwards", [])

        mid = team.players.get("Midfielders", [])

        def avg(stat_getter, players):

            vals = [stat_getter(p) or 0 for p in players]

            return sum(vals) / len(vals) if vals else 0

        avg_fwd_shoot = avg(lambda p: p.shooting, fwd)

        avg_mid_pass = avg(lambda p: p.passing, mid)

        return 0.7 * avg_fwd_shoot + 0.3 * avg_mid_pass



    def _team_defense_value(self, team: Teams) -> float:

        defs = team.players.get("Defenders", [])

        vals = [p.defending or 0 for p in defs]

        return sum(vals) / len(vals) if vals else 1.0



    def _choose_scorer(self, team: Teams):

        fwd = team.players.get("Forwards", [])

        mid = team.players.get("Midfielders", [])

        if fwd:

            items = fwd

            weights = [(p.shooting or 10) for p in fwd]

            return _weighted_choice(items, weights)

        if mid:

            items = mid

            weights = [(p.passing or 5) for p in mid]

            return _weighted_choice(items, weights)

        allp = team.all_players()

        return random.choice(allp) if allp else None



    def _simulate_substitutions(self):

        for team in (self.home, self.away):

            max_subs = 5

            subs_done = 0

            candidates = []

            for grp in ("Goalkeeper", "Defenders", "Midfielders", "Forwards"):

                for p in list(team.players.get(grp, [])):

                    if p.hasRed:

                        continue

                    if p.hasYellow:

                        candidates.append((grp, p))

            for grp, p in candidates:

                if subs_done >= max_subs:

                    break

                if random.random() < 0.7 and team.bench:

                    bench_choice = None

                    for b in team.bench:

                        if not b.isInjured and not b.hasRed:

                            bench_choice = b

                            break

                    if bench_choice is None:

                        continue

                    team.bench = [x for x in team.bench if x.long_name != bench_choice.long_name]

                    team.players[grp] = [x for x in team.players[grp] if x.long_name != p.long_name]

                    team.players[grp].append(bench_choice)

                    team.bench.append(p)

                    subs_done += 1

                    minute = random.randint(46, 90)

                    self.timeline.append({"minute": minute, "type": "sub", "team": team.name, "out": p.long_name, "in": bench_choice.long_name})



    def _starting_players(self, team: Teams) -> List[Player]:

        out = []

        for grp in ("Goalkeeper", "Defenders", "Midfielders", "Forwards"):

            out.extend(team.players.get(grp, []))

        return out



    def _simulate_goals_period(self, minutes_start: int, minutes_end: int, lam: float):

        total_goals = _poisson(lam)

        minutes = sorted(random.randint(minutes_start, minutes_end) for _ in range(total_goals))

        home_attack = self._team_attack_value(self.home)

        away_attack = self._team_attack_value(self.away)

        home_def = self._team_defense_value(self.home)

        away_def = self._team_defense_value(self.away)

        home_score_weight = max(0.01, home_attack / (away_def or 1))

        away_score_weight = max(0.01, away_attack / (home_def or 1))

        for minute in minutes:

            t = _weighted_choice([self.home, self.away], [home_score_weight, away_score_weight])

            scorer = self._choose_scorer(t)

            if scorer is None:

                continue

            # compute attacker and keeper influence

            opponent = self.away if t is self.home else self.home

            def keeper_metric(team: Teams) -> float:

                gklist = team.players.get("Goalkeeper", [])

                if gklist:

                    gk = gklist[0]

                    vals = [v for v in (gk.gk_diving, gk.gk_reflexes, gk.gk_positioning) if v]

                    if vals:

                        return sum(vals) / len(vals)

                    return gk.overall or 50

                allp = team.all_players()

                return allp[0].overall if allp else 50



            attacker_shoot = scorer.shooting or scorer.overall or 50

            attacker_pace = scorer.pace or scorer.overall or 50

            attacker_skill = 0.7 * attacker_shoot + 0.3 * attacker_pace

            keeper_skill = keeper_metric(opponent)

            # team factor from attack/defense

            team_factor = home_score_weight if t is self.home else away_score_weight

            # attacker / defender counts influence

            atk_count = len(t.players.get("Forwards", [])) + 0.5 * len(t.players.get("Midfielders", []))

            def_count = len(opponent.players.get("Defenders", []))

            atk_count = max(1.0, atk_count)

            def_count = max(1.0, def_count)

            adv = atk_count / def_count

            # give attackers more edge when they outnumber defenders

            adv_factor = min(4.0, max(0.6, adv))

            # probability of converting this chance into a goal

            skill_factor = attacker_skill / (attacker_skill + keeper_skill)

            # base multiplier strongly favoring attackers

            base_mul = 0.5

            # allow a larger contribution from team attack/defense balance

            team_mul = min(3.2, team_factor)

            prob = base_mul * skill_factor * team_mul * adv_factor

            # boost if attacker skill significantly exceeds keeper

            if attacker_skill - keeper_skill > 8:

                boost = min(2.0, 1.0 + (attacker_skill - keeper_skill) / 80.0)

                prob *= boost

            prob = max(0.04, min(0.999, prob))

            scored = random.random() < prob

            if scored:

                self.score[t.name] += 1

                ev = {"minute": minute, "type": "goal", "team": t.name, "scorer": scorer.long_name}

                self.timeline.append(ev)

            else:

                # missed big chance

                ev = {"minute": minute, "type": "chance", "team": t.name, "player": scorer.long_name}

                self.timeline.append(ev)



    def _simulate_penalties(self) -> List[str]:

        messages: List[str] = []

        def pick_pen_order(team: Teams) -> List[Player]:

            starters = [p for p in self._starting_players(team) if not p.isInjured and not p.hasRed]

            bench_ok = [b for b in team.bench if not b.isInjured and not b.hasRed]

            candidates = starters + bench_ok

            def score(p: Player):

                return (p.mentality_penalties or 50) * 2 + (p.overall or 0)

            candidates.sort(key=score, reverse=True)

            takers = []

            seen = set()

            for p in candidates:

                key = p.long_name.lower()

                if key in seen:

                    continue

                takers.append(p)

                seen.add(key)

                if len(takers) >= 5:

                    break

            return takers



        home_takers = pick_pen_order(self.home)

        away_takers = pick_pen_order(self.away)



        def keeper_overall(team: Teams) -> int:

            gk = team.players.get("Goalkeeper", [])

            if gk:

                g = gk[0]

                vals = [v for v in (g.gk_reflexes, g.gk_diving, g.gk_positioning) if v]

                if vals:

                    return sum(vals) / len(vals)

                return g.overall or 50

            allp = team.all_players()

            return allp[0].overall if allp else 50



        home_keeper = keeper_overall(self.away)

        away_keeper = keeper_overall(self.home)

        home_pen = 0

        away_pen = 0

        pen_events = []

        for i in range(5):

            minute_h = 121 + i * 2

            taker_h = home_takers[i] if i < len(home_takers) else (home_takers[i % len(home_takers)] if home_takers else None)

            if taker_h:

                shooter_shoot = taker_h.shooting or taker_h.overall or 50

                shooter_ment = taker_h.mentality_penalties or 50

                prob = 0.725 + (shooter_ment - 50) / 200.0 + (shooter_shoot - 50) / 300.0 - ((home_keeper or 50) - 50) / 250.0

                prob = max(0.03, min(0.98, prob))

                scored_h = random.random() < prob

                if scored_h:

                    home_pen += 1

                pen_events.append((minute_h, self.home.name, taker_h.long_name, scored_h))

            minute_a = minute_h + 1

            taker_a = away_takers[i] if i < len(away_takers) else (away_takers[i % len(away_takers)] if away_takers else None)

            if taker_a:

                shooter_shoot = taker_a.shooting or taker_a.overall or 50

                shooter_ment = taker_a.mentality_penalties or 50

                prob = 0.725 + (shooter_ment - 50) / 200.0 + (shooter_shoot - 50) / 300.0 - ((away_keeper or 50) - 50) / 250.0

                prob = max(0.03, min(0.98, prob))

                scored_a = random.random() < prob

                if scored_a:

                    away_pen += 1

                pen_events.append((minute_a, self.away.name, taker_a.long_name, scored_a))



        for m, team_name, taker_name, scored in pen_events:

            self.timeline.append({"minute": m, "type": "pen", "team": team_name, "taker": taker_name, "scored": scored})



        sd_index = 0

        while home_pen == away_pen:

            minute_h = 121 + 5 * 2 + sd_index * 2

            taker_h = home_takers[sd_index % len(home_takers)] if home_takers else None

            taker_a = away_takers[sd_index % len(away_takers)] if away_takers else None

            scored_h = False

            scored_a = False

            if taker_h:

                shooter_shoot = taker_h.shooting or taker_h.overall or 50

                shooter_ment = taker_h.mentality_penalties or 50

                prob = 0.725 + (shooter_ment - 50) / 200.0 + (shooter_shoot - 50) / 300.0 - ((home_keeper or 50) - 50) / 250.0

                prob = max(0.03, min(0.98, prob))

                scored_h = random.random() < prob

                if scored_h:

                    home_pen += 1

                self.timeline.append({"minute": minute_h, "type": "pen", "team": self.home.name, "taker": taker_h.long_name, "scored": scored_h})

            minute_a = minute_h + 1

            if taker_a:

                shooter_shoot = taker_a.shooting or taker_a.overall or 50

                shooter_ment = taker_a.mentality_penalties or 50

                prob = 0.725 + (shooter_ment - 50) / 200.0 + (shooter_shoot - 50) / 300.0 - ((away_keeper or 50) - 50) / 250.0

                prob = max(0.03, min(0.98, prob))

                scored_a = random.random() < prob

                if scored_a:

                    away_pen += 1

                self.timeline.append({"minute": minute_a, "type": "pen", "team": self.away.name, "taker": taker_a.long_name, "scored": scored_a})

            sd_index += 1

            if home_pen != away_pen:

                break



        if home_pen > away_pen:

            self.score[self.home.name] += 1

            self.timeline.append({"minute": 999, "type": "penwin", "team": self.home.name, "detail": f"{home_pen}-{away_pen}"})

        else:

            self.score[self.away.name] += 1

            self.timeline.append({"minute": 999, "type": "penwin", "team": self.away.name, "detail": f"{away_pen}-{home_pen}"})



        return [ (e['minute'], e) for e in [ev for ev in self.timeline if ev.get('type')=='pen'] ]



    def _simulate_cards(self):

        yellow_counts = defaultdict(int)

        def _remove_player(team: Teams, player: Player):

            for grp in list(team.players.keys()):

                team.players[grp] = [x for x in team.players[grp] if x.long_name != player.long_name]

            team.bench = [x for x in team.bench if x.long_name != player.long_name]

            player.hasRed = True

            player.isInjured = True

        for team in (self.home, self.away):

            for p in list(team.all_players()):

                aggr = (p.aggression or 50) / 100.0

                yellow_prob = 0.02 * (0.5 + aggr)

                red_prob = 0.002 * (0.5 + aggr)

                if random.random() < red_prob:

                    minute = random.randint(1, 90)

                    self.timeline.append({"minute": minute, "type": "red", "team": team.name, "player": p.long_name})

                    _remove_player(team, p)

                    continue

                if random.random() < yellow_prob:

                    yellow_counts[(team.name, p.long_name)] += 1

                    minute = random.randint(1, 90)

                    self.timeline.append({"minute": minute, "type": "yellow", "team": team.name, "player": p.long_name})

                    if yellow_counts[(team.name, p.long_name)] >= 2:

                        minute2 = random.randint(minute, 90)

                        self.timeline.append({"minute": minute2, "type": "red", "team": team.name, "player": p.long_name})

                        _remove_player(team, p)



    def simulate(self) -> dict:

        self.timeline = []

        self.score = {self.home.name: 0, self.away.name: 0}

        self._simulate_goals_period(1, 90, self.AVG_XG)

        self.timeline.append({"minute": 45, "type": "halftime"})

        self._simulate_cards()

        self._simulate_substitutions()

        messages: List[str] = []

        went_to_et = False

        if self.knockout and self.score[self.home.name] == self.score[self.away.name]:

            went_to_et = True

            self.timeline.append({"minute": 91, "type": "et_start"})

            lam_et = self.AVG_XG * (30.0 / 90.0)

            self._simulate_goals_period(91, 120, lam_et)

            self.timeline.append({"minute": 105, "type": "et_half"})

            self._simulate_cards()

            self._simulate_substitutions()

            if self.score[self.home.name] == self.score[self.away.name]:

                self.timeline.append({"minute": 121, "type": "penalties"})

                pen_ev = self._simulate_penalties()

        self.timeline.sort(key=lambda e: e.get("minute", 0))

        for ev in self.timeline:

            if ev["type"] == "goal":

                messages.append(f"{ev['minute']}' - GOAL - {ev['team']}: {ev['scorer']}")

            elif ev["type"] == "yellow":

                messages.append(f"{ev['minute']}' - YELLOW - {ev['team']}: {ev['player']}")

            elif ev["type"] == "red":

                messages.append(f"{ev['minute']}' - RED - {ev['team']}: {ev['player']}")

            elif ev["type"] == "sub":

                messages.append(f"{ev['minute']}' - SUB - {ev['team']}: OUT {ev['out']} IN {ev['in']}")

            elif ev["type"] == "pen":

                scored = ev.get("scored")

                if scored:

                    messages.append(f"{ev['minute']}' - PENALTY - {ev['team']}: {ev.get('taker')} SCORES")

                else:

                    messages.append(f"{ev['minute']}' - PENALTY - {ev['team']}: {ev.get('taker')} MISSES")

            elif ev["type"] == "penwin":

                messages.append(f"{ev.get('team')} win penalty shootout {ev.get('detail')}")

            elif ev["type"] == "halftime":

                messages.append(f"{ev['minute']}' - HALFTIME")

            elif ev["type"] == "et_start":

                messages.append(f"{ev['minute']}' - EXTRA TIME START")

            elif ev["type"] == "et_half":

                messages.append(f"{ev['minute']}' - EXTRA TIME HALFTIME")

            elif ev["type"] == "penalties":

                messages.append(f"{ev['minute']}' - PENALTIES TO FOLLOW")

        if went_to_et and self.knockout and self.score[self.home.name] == self.score[self.away.name]:

            score_msg = f"FT (pens) {self.home.name} {self.score[self.home.name]} - {self.score[self.away.name]} {self.away.name}"

        elif went_to_et:

            score_msg = f"AET {self.home.name} {self.score[self.home.name]} - {self.score[self.away.name]} {self.away.name}"

        else:

            score_msg = f"FT {self.home.name} {self.score[self.home.name]} - {self.score[self.away.name]} {self.away.name}"

        messages.append("\n" + score_msg)

       

        return {"timeline": self.timeline, "messages": messages, "score": self.score}



    def __str__(self) -> str:

        res = self.simulate()

        return "\n".join(res["messages"])

