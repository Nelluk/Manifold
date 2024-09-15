import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import supybot.log as log
import requests
import json
from urllib.parse import quote

class Manifold(callbacks.Plugin):
    """Fetches and displays odds from Manifold.markets"""

    def _fetch_manifold_data(self, query, max_results=7):
        """
        Fetch and parse Manifold.markets data from API.
        
        Args:
            query (str): Search term or URL
            max_results (int): Maximum number of outcomes to return

        Returns:
            dict: Parsed event data with title and outcomes
        """
        # Prepare API query
        encoded_query = quote(query)
        search_api_url = f"https://api.manifold.markets/v0/search-markets?term={encoded_query}&sort=liquidity&filter=open&contractType=ALL&limit=1"
        
        log.debug(f"Manifold: Fetching data from API URL: {search_api_url}")
        
        # Fetch data from search API
        response = requests.get(search_api_url)
        response.raise_for_status()
        search_data = response.json()

        if not search_data:
            return {'title': "No matching market found", 'data': []}

        market = search_data[0]
        title = market['question']
        volume = market['volume']
        bettors = market['uniqueBettorCount']
        
        if market['outcomeType'] == 'BINARY':
            # Simple yes/no market
            probability = market['probability']
            data = [('Yes', probability, volume)]
        else:
            # Multiple choice market
            slug = market['slug']
            market_api_url = f"https://api.manifold.markets/v0/slug/{slug}"
            
            log.debug(f"Manifold: Fetching market data from API URL: {market_api_url}")
            
            # Fetch data from market API
            market_response = requests.get(market_api_url)
            market_response.raise_for_status()
            market_data = market_response.json()
            
            answers = market_data['answers']
            data = [(answer['text'], answer['probability'], volume) for answer in answers]
            data.sort(key=lambda x: x[1], reverse=True)
            data = data[:max_results]

        result = {
            'title': title,
            'data': data,
            'volume': volume,
            'bettors': bettors
        }
        
        log.debug(f"Manifold: Parsed market data: {result}")
        
        return result

    def manifold(self, irc, msg, args, query):
        """<query>
        
        Fetches and displays the current odds from Manifold.markets. 
        <query> can be a search term or a Manifold.markets URL.
        """
        try:
            result = self._fetch_manifold_data(query)
            if result['data']:
                # Format volume
                volume = result['volume']
                if volume >= 1000000:
                    volume_str = f"{volume/1000000:.0f}M"
                elif volume >= 1000:
                    volume_str = f"{volume/1000:.0f}k"
                else:
                    volume_str = f"{volume:.0f}"

                # Format output
                output = f"\x02{result['title']}\x02 (Volume: {volume_str}, Bettors: {result['bettors']}): "
                output += " | ".join([f"{outcome}: \x02{probability:.1%}\x02" for outcome, probability, _ in result['data']])
                
                log.debug(f"Manifold: Sending IRC reply: {output}")
                
                # Reply in the same channel, without nick prefix
                irc.reply(output, prefixNick=False)
            else:
                irc.reply("Unable to fetch odds or no valid data found.")
        except Exception as e:
            irc.reply(f"An error occurred: {str(e)}")

    manifold = wrap(manifold, ['text'])

Class = Manifold

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
