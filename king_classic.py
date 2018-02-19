import pandas as pd
import numpy as np
import sys
import pickle
import pdb
from pymongo import MongoClient
from collections import defaultdict
from scipy.stats import rankdata
import folium


def past_locations_map():
    m = folium.Map(location=[40, -98], zoom_start=5)

    folium.Marker([36.805531, -114.06719], popup='2017 - Mesquite, NV - Alex King').add_to(m)
    folium.Marker([41.878114, -87.629798], popup='2016 - Chicago, IL - Jerry King').add_to(m)
    folium.Marker([34.502587, -84.951054], popup='2015 - Georgia - Stuart King').add_to(m)
    folium.Marker([42.331427, -83.045754], popup='2014 - Michigan - Reggie Sherrill').add_to(m)
    folium.Marker([39.739236, -104.990251], popup='2013 - Denver, CO - Stuart King').add_to(m)
    folium.Marker([47.677683, -116.780466], popup="2012 - Coeur d'Alene, ID - Jerry King").add_to(m)
    folium.Marker([37.096528, -113.568416], popup='2011 - St. George, UT - Reggie Sherrill').add_to(m)
    folium.Marker([38.291859, -122.458036], popup='2010 - Northern California - Alex King').add_to(m)
    folium.Marker([39.237685, -120.02658], popup='2009 - Lake Tahoe, CA - Alex King').add_to(m)
    folium.Marker([47.606209, -122.332071], popup='2008 - Seattle, WA - Alex King').add_to(m)
    folium.Marker([35.960638, -83.920739], popup='2007 - Tennessee - Stuart King').add_to(m)
    folium.Marker([33.520661, -86.80249], popup='2006 - Alabama - Gary Olson').add_to(m)
    folium.Marker([32.366805, -86.299969], popup='2005 - Alabama - Stuart King').add_to(m)

    m.save('templates/past_locations.html')


class Player(object):

    def __init__(self, name, hdcp, courses, skins=True):
        self.name = name
        self.skins = skins
        self.hdcp = hdcp
        self.scores = dict()

        for course, par in courses.items():
            self.create_scorecard(course)


    def create_scorecard(self, course):
        self.scores[course] = dict((x,0) for x in range(1,19))


    def post_score(self, course, hole, score):
        self.scores[course][hole] = score


    def show_scorecard(self, course):
        return self.scores[course]


    def front_nine(self, course):
        front = [v for k, v in self.scores[course].items()][:9]
        return front


    def back_nine(self, course):
        back = [v for k, v in self.scores[course].items()][9:]
        return back


    def calc_course_score(self, course, net=False):
        if net:
            net_score = (sum(self.scores[course].values()) - self.hdcp)
            return net_score

        score = sum(self.scores[course].values())
        return score


    def calc_total_score(self, net=False):
        if net:
            total = 0
            for course in self.scores.keys():
                net_total += (sum(self.scores[course].values()) - self.hdcp)
            return net_total

        total = 0
        for course in self.scores.keys():
            total += sum(self.scores[course].values())
        return total



class PlayGolf(object):

    def __init__(self, year):
        self.year = year
        self.client = MongoClient()
        # self.client.drop_database('kc_2018')
        self.db = self.client['kc_{}'.format(year)] # Access/Initiate Database
        self.coll = self.db['scores'] # Access/Initiate Table
        self.courses = {"Talking Stick - O'odham" : [4,5,4,4,4,3,4,3,4,4,3,4,4,4,4,3,5,4],
        'Talking Stick - Piipaash' : [4,4,3,4,4,4,5,4,3,4,4,4,3,5,4,5,3,4],
        'Wildfire - Palmer' : [4,4,5,4,3,4,4,3,5,4,5,4,3,5,3,4,4,4],
        'Wildfire - Faldo' : [4,4,3,4,4,4,3,4,5,4,5,4,4,3,5,4,3,4],
        "Whirlwind - Devil's Claw" : [4,4,5,3,4,5,3,4,4,4,4,3,4,3,5,4,5,4],
        'Whirlwind - Cattail' : [4,5,3,4,4,3,5,4,4,3,4,5,4,4,3,4,5,4]}


    def add_player(self, name, hdcp, skins=True):
        golfer = Player(name, hdcp, self.courses, skins)
        golfer_pkl = pickle.dumps(golfer)
        self.coll.update_one({'name': name}, {'$set': {'name': name, 'player': golfer_pkl, 'skins': skins, 'hdcp': hdcp}}, upsert=True)


    def add_score(self, player, course, hole, score):
        doc = self.coll.find_one({'name': player})
        golfer = pickle.loads(doc['player'])
        golfer.post_score(course, hole, score)

        golfer_pkl = pickle.dumps(golfer)
        self.coll.update_one({'name': player}, {'$set': {'player': golfer_pkl}})


    def show_player_course_score(self, player, course, net=False):
        doc = self.coll.find_one({'name': player})
        golfer = pickle.loads(doc['player'])
        score = golfer.calc_course_score(course, net)
        return score


    def show_player_total_score(self, player, net=False):
        doc = self.coll.find_one({'name': player})
        golfer = pickle.loads(doc['player'])
        total_score = golfer.calc_total_score(net)
        return total_score


    def show_team_score(self, team, course):
        team_score = team.calc_team_score(course)
        return 'Team: {}, Score: {}'.format(team.keys())


    def leaderboard(self, net=True):
        names = []
        players = []
        docs = self.coll.find()
        for doc in docs:
            names.append(doc['name'])
            players.append(pickle.loads(doc['player']))

        scores = []
        for player in players:
            total = 0
            for course in player.scores.keys():
                if player.calc_course_score(course, net) > 0:
                    total += player.calc_course_score(course, net)
            scores.append(total)

        rank = list(rankdata(scores, method='min'))
        # rank = list(np.unique(scores, return_inverse=True)[1])
        results = list(zip(rank, names, scores))
        sorted_results = sorted(results, key=lambda x: x[0])


        df = pd.DataFrame(sorted_results, columns=['Position', 'Name', 'Net Total'])
        # df.set_index('Position', inplace=True)

        return df


    def calc_skins(self, course):
        names = []
        players = []
        docs = self.coll.find()
        for doc in docs:
            if doc['skins'] == True:
                names.append(doc['name'])
                players.append(pickle.loads(doc['player']))

        pot = len(names) * 10
        cols = [str(x) for x in range(1, 19)]

        scores = []
        for player in players:
            scores.append(list(player.scores[course].values()))

        df = pd.DataFrame(data=scores, index=names, columns=cols)
        low_scores = df.min(axis=0)
        skins = []
        for hole, low_score in zip(range(1, 19), low_scores):
            scores = list(df[str(hole)].values)
            if scores.count(low_score) == 1:
                skins.append(df[str(hole)].idxmin())

        results = []
        for name in names:
            results.append((name, skins.count(name)))

        sorted_results = sorted(results, key=lambda x: x[1], reverse=True)

        total_skins = sum(n for _, n in sorted_results)
        skin_value = pot / total_skins

        final_results = [(name, skins * skin_value) for name, skins in sorted_results]

        df_results = [(name, int(winnings/skin_value), float(winnings)) for name, winnings in final_results]

        df = pd.DataFrame(df_results, columns=['Player', 'Skins', 'Winnings'])
        df['Winnings'] = df['Winnings'].map('${:,.2f}'.format)

        return df


    def player_scorecards(self, players, course):
        course_par = self.courses[course]
        front_par = sum(course_par[:9])
        back_par = sum(course_par[9:])
        total_par = sum(course_par)
        par = course_par[:9] + [front_par] + course_par[9:] + [back_par, total_par, 0, 0]
        scores = [par]

        for player in players:
            doc = self.coll.find_one({'name': player})
            golfer = pickle.loads(doc['player'])

            front = golfer.front_nine(course)
            front_tot = sum(front)
            back = golfer.back_nine(course)
            back_tot = sum(back)
            total = golfer.calc_course_score(course)
            net_total = golfer.calc_course_score(course, net=True)

            score = front + [front_tot] + back + [back_tot, total, golfer.hdcp, net_total]
            scores.append(score)

        idx = ['Par'] + players.copy()

        cols = [str(x) for x in range(1, 19)]
        all_cols = cols[:9] + ['Front'] + cols[9:] + ['Back', 'Total', 'Hdcp', 'Net']

        df = pd.DataFrame(data=scores, index=idx, columns=all_cols)
        for col in df.columns:
            df[col] = df[col].astype(str)
        df.loc['Par'] = df.loc['Par'].replace(['0'],'')
        return df


if __name__ == '__main__':
    past_locations_map()
    # golf = PlayGolf('2018')
    #
    # print('Adding players...')
    # golf.add_player('Stuart', 2, True)
    # golf.add_player('Alex', 1, True)
    # golf.add_player('Jerry', 5, True)
    # golf.add_player('Reggie', 5, True)
    #
    # print("Adding Stuart's scores...")
    # for idx, _ in enumerate(range(18)):
    #     golf.add_score('Stuart', 'Talking Stick - Piipaash', idx+1, np.random.randint(3,6))
    #     golf.add_score('Stuart', "Talking Stick - O'odham", idx+1, np.random.randint(3,6))
    #
    # print("Adding Alex's scores...")
    # for idx, _ in enumerate(range(18)):
    #     golf.add_score('Alex', 'Talking Stick - Piipaash', idx+1, np.random.randint(3,6))
    #     golf.add_score('Alex', "Talking Stick - O'odham", idx+1, np.random.randint(3,6))
    #
    # print("Adding Jerry's scores...")
    # for idx, _ in enumerate(range(18)):
    #     golf.add_score('Jerry', 'Talking Stick - Piipaash', idx+1, np.random.randint(3,7))
    #     golf.add_score('Jerry', "Talking Stick - O'odham", idx+1, np.random.randint(3,7))
    #
    # print("Adding Reggie's scores...")
    # for idx, _ in enumerate(range(18)):
    #     golf.add_score('Reggie', 'Talking Stick - Piipaash', idx+1, np.random.randint(3,7))
    #     golf.add_score('Reggie', "Talking Stick - O'odham", idx+1, np.random.randint(3,7))
