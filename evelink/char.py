from evelink import api
from evelink import constants
from evelink.parsing.industry_jobs import parse_industry_jobs

class Char(object):
    """Wrapper around /char/ of the EVE API.

    Note that a valid API key is required.
    """

    def __init__(self, char_id, api):
        self.api = api
        self.char_id = char_id

    def wallet_journal(self, before_id=None, limit=None):
        """Returns a complete record of all wallet activity for a specified character"""
        params = {'characterID': self.char_id}
        if before_id is not None:
            params['fromID'] = before_id 
        if limit is not None:
            params['rowCount'] = limit 
        api_result = self.api.get('char/WalletJournal', params)

        rowset = api_result.find('rowset')
        result = []

        for row in rowset.findall('row'):
            a = row.attrib
            entry = {
                'timestamp': api.parse_ts(a['date']),
                'id': int(a['refID']),
                'type_id': int(a['refTypeID']),
                'party_1': {
                    'name': a['ownerName1'],
                    'id': int(a['ownerID1']),
                },
                'party_2': {
                    'name': a['ownerName2'],
                    'id': int(a['ownerID2']),
                },
                'arg': {
                    'name': a['argName1'],
                    'id': int(a['argID1']),
                },
                'amount': float(a['amount']),
                'balance': float(a['balance']),
                'reason': a['reason'],
                'tax': {
                    'taxer_id': int(a['taxReceiverID'] or 0),
                    'amount': float(a['taxAmount'] or 0),
                },
            }

            result.append(entry)

        result.sort(key=lambda x: x['id'])
        return result

    def wallet_info(self):
        """Return a given character's wallet."""
        api_result = self.api.get('char/AccountBalance',
            {'characterID': self.char_id})

        rowset = api_result.find('rowset')
        row = rowset.find('row')
        result = { 
            'balance': float(row.attrib['balance']),
            'id': int(row.attrib['accountID']),
            'key': int(row.attrib['accountKey']),
        }
        return result

    def wallet_balance(self):
        """Helper to return just the balance from a given character wallet"""

        return self.wallet_info()['balance']

    def industry_jobs(self):
        """Get a list of jobs for a character"""

        api_result = self.api.get('char/IndustryJobs',
            {'characterID': self.char_id})

        return parse_industry_jobs(api_result)

    def kills(self, before_kill=None):
        """Look up recent kills for the given character

        before_kill:
            Optional. Only show kills before this kill id. (Used for paging.)
        """

        params = {'characterID': self.char_id}
        if before_kill is not None:
            params['beforeKillID'] = before_kill
        api_result = self.api.get('char/KillLog', params)

        rowset = api_result.find('rowset')
        result = {}
        for row in rowset.findall('row'):
            a = row.attrib
            kill_id = int(a['killID'])
            result[kill_id] = {
                'id': kill_id,
                'system_id': int(a['solarSystemID']),
                'time': api.parse_ts(a['killTime']),
                'moon_id': int(a['moonID']),
            }

            victim = row.find('victim')
            a = victim.attrib
            result[kill_id]['victim'] = {
                'id': int(a['characterID']),
                'name': a['characterName'],
                'corp': {
                    'id': int(a['corporationID']),
                    'name': a['corporationName'],
                },
                'alliance': {
                    'id': int(a['allianceID']),
                    'name': a['allianceName'],
                },
                'faction': {
                    'id': int(a['factionID']),
                    'name': a['factionName'],
                },
                'damage': int(a['damageTaken']),
                'ship_type_id': int(a['shipTypeID']),
            }

            result[kill_id]['attackers'] = {}

            rowsets = {}
            for rowset in row.findall('rowset'):
                key = rowset.attrib['name']
                rowsets[key] = rowset

            for attacker in rowsets['attackers'].findall('row'):
                a = attacker.attrib
                attacker_id = int(a['characterID'])
                result[kill_id]['attackers'][attacker_id] = {
                    'id': attacker_id,
                    'name': a['characterName'],
                    'corp': {
                        'id': int(a['corporationID']),
                        'name': a['corporationName'],
                    },
                    'alliance': {
                        'id': int(a['allianceID']),
                        'name': a['allianceName'],
                    },
                    'faction': {
                        'id': int(a['factionID']),
                        'name': a['factionName'],
                    },
                    'sec_status': float(a['securityStatus']),
                    'damage': int(a['damageDone']),
                    'final_blow': a['finalBlow'] == '1',
                    'weapon_type_id': int(a['weaponTypeID']),
                    'ship_type_id': int(a['shipTypeID']),
                }

            result[kill_id]['items'] = {}
            for item in rowsets['items'].findall('row'):
                a = item.attrib
                type_id = int(a['typeID'])
                result[kill_id]['items'][type_id] = {
                    'id': type_id,
                    'flag': int(a['flag']),
                    'dropped': int(a['qtyDropped']),
                    'destroyed': int(a['qtyDestroyed']),
                }
            
        return result

    def orders(self):
        """Return a given character's buy and sell orders."""
        api_result = self.api.get('char/MarketOrders',
            {'characterID': self.char_id})

        rowset = api_result.find('rowset')
        rows = rowset.findall('row')
        result = {}
        for row in rows:
            a = row.attrib
            id = int(a['orderID'])
            result[id] = {
                'id': id,
                'char_id': int(a['charID']),
                'station_id': int(a['stationID']),
                'amount': int(a['volEntered']),
                'amount_left': int(a['volRemaining']),
                'status': constants.Market().order_status[int(a['orderState'])],
                'type_id': int(a['typeID']),
                'range': int(a['range']),
                'account_key': int(a['accountKey']),
                'duration': int(a['duration']),
                'escrow': float(a['escrow']),
                'price': float(a['price']),
                'type': 'buy' if a['bid'] == '1' else 'sell',
                'timestamp': api.parse_ts(a['issued']),
            }

        return result

    def research(self):
        """Returns information about the agents with whom the character is doing research."""

        api_result = self.api.get('char/Research',
            {'characterID': self.char_id})

        rowset = api_result.find('rowset')
        rows = rowset.findall('row')
        result = {}
        for row in rows:
            a = row.attrib
            id = int(a['agentID'])
            result[id] = {
                'id': id,
                'skill_id': int(a['skillTypeID']),
                'timestamp': api.parse_ts(a['researchStartDate']),
                'per_day': float(a['pointsPerDay']),
                'remaining': float(a['remainderPoints']),
            }

        return result

    def current_training(self):
        """Returns the skill that is currently being trained by a specified character"""

        api_result = self.api.get('char/SkillInTraining',
            {'characterID': self.char_id})

        _str, _int, _float, _bool, _ts = api.elem_getters(api_result)
        result = {
            'start_ts': _ts('trainingStartTime'),
            'end_ts': _ts('trainingEndTime'),
            'type_id': _int('trainingTypeID'),
            'start_sp': _int('trainingStartSP'),
            'end_sp': _int('trainingDestinationSP'),
            'current_ts': _ts('currentTQTime'),
            'level': _int('trainingToLevel'),
            'active': _bool('skillInTraining'),
        }

        return result

    def skill_queue(self):
        """returns the skill queue of the character"""
        api_result = self.api.get('char/SkillQueue',
            {'characterID': self.char_id})

        rowset = api_result.find('rowset')
        rows = rowset.findall('row')
        result = []
        for row in rows:
            a = row.attrib
            line = {
                'position': int(a['queuePosition']),
                'type_id': int(a['typeID']),
                'level': int(a['level']),
                'start_sp': int(a['startSP']),
                'end_sp': int(a['endSP']),
                'start_ts': api.parse_ts(a['startTime']),
                'end_ts': api.parse_ts(a['endTime']),
            }

            result.append(line)

        return result

    def messages(self):
        """Returns a list of headers for a character's mail."""
        api_result = self.api.get('char/MailMessages',
            {'characterID': self.char_id})

        rowset = api_result.find('rowset')
        results = []
        for row in rowset.findall('row'):
            a = row.attrib
            message = {
                'id': int(a['messageID']),
                'sender_id': int(a['senderID']),
                'timestamp': api.parse_ts(a['sentDate']),
                'title': a['title'],
                'to': {},
            }

            org_id = a['toCorpOrAllianceID']
            message['to']['org_id'] = int(org_id) if org_id else None

            char_ids = a['toCharacterIDs']
            message['to']['char_ids'] = [int(i) for i in char_ids.split(',')] if char_ids else None

            list_ids = a['toListID']
            message['to']['list_ids'] = [int(i) for i in list_ids.split(',')] if list_ids else None

            results.append(message)

        return results
