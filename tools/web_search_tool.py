# tools/web_search_tool.py

import requests
from typing import List, Dict, Optional, Literal
from datetime import datetime
import time


class WebSearchTool:
    """
    Web Search Tool with multiple provider support

    Supports:
    - Google Custom Search API (recommended)
    - Serper API (alternative)
    - Tavily API (alternative)

    Usage:
        # Google (using provided credentials)
        tool = WebSearchTool(
            provider="google",
            api_key="AIzaSyBwMrXdSmphU4I3J2iE6n7uYyFJnRoLQm8",
            search_engine_id="856c1692fc3734c35"
        )

        results = tool.search("taux de change XOF EUR", num_results=5, language="fr")
    """

    def __init__(
        self,
        provider: Literal["google", "serper", "tavily"] = "google",
        api_key: Optional[str] = None,
        search_engine_id: Optional[str] = None,
        timeout: int = 10
    ):
        """
        Initialize web search tool

        Args:
            provider: Search provider ("google", "serper", "tavily")
            api_key: API key for the provider
            search_engine_id: Google Custom Search Engine ID (Google only)
            timeout: Request timeout in seconds
        """
        self.provider = provider
        self.api_key = api_key
        self.search_engine_id = search_engine_id
        self.timeout = timeout

        # Validate configuration
        if provider == "google" and not search_engine_id:
            raise ValueError("search_engine_id required for Google Custom Search")

        if not api_key:
            raise ValueError("api_key required")

        # Provider endpoints
        self.endpoints = {
            "google": "https://www.googleapis.com/customsearch/v1",
            "serper": "https://google.serper.dev/search",
            "tavily": "https://api.tavily.com/search"
        }

    def search(
        self,
        query: str,
        num_results: int = 5,
        language: str = "fr",
        time_range: str = "any",  # any, day, week, month, year
        safe_search: bool = True
    ) -> List[Dict]:
        """
        Perform web search

        Args:
            query: Search query
            num_results: Number of results to return (max 10)
            language: Language code (fr, en, etc.)
            time_range: Time range filter
            safe_search: Enable safe search

        Returns:
            List of search results with:
            - title: Result title
            - url: Result URL
            - snippet: Result description
            - source: Source domain
            - date: Publication date (if available)
            - position: Result position
        """
        if self.provider == "google":
            return self._search_google(query, num_results, language, time_range, safe_search)
        elif self.provider == "serper":
            return self._search_serper(query, num_results, language, time_range)
        elif self.provider == "tavily":
            return self._search_tavily(query, num_results, language)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def _search_google(
        self,
        query: str,
        num_results: int,
        language: str,
        time_range: str,
        safe_search: bool
    ) -> List[Dict]:
        """Google Custom Search API implementation"""
        params = {
            'key': self.api_key,
            'cx': self.search_engine_id,
            'q': query,
            'num': min(num_results, 10),  # Google max is 10
            'lr': f'lang_{language}',
            'safe': 'active' if safe_search else 'off'
        }

        # Add time range filter
        if time_range != "any":
            date_restrict_map = {
                'day': 'd1',
                'week': 'w1',
                'month': 'm1',
                'year': 'y1'
            }
            if time_range in date_restrict_map:
                params['dateRestrict'] = date_restrict_map[time_range]

        try:
            response = requests.get(
                self.endpoints['google'],
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            results = []
            if 'items' in data:
                for idx, item in enumerate(data['items'], 1):
                    result = {
                        'title': item.get('title', ''),
                        'url': item.get('link', ''),
                        'snippet': item.get('snippet', ''),
                        'source': self._extract_domain(item.get('link', '')),
                        'position': idx,
                        'provider': 'google'
                    }

                    # Extract date if available
                    if 'pagemap' in item and 'metatags' in item['pagemap']:
                        metatags = item['pagemap']['metatags'][0]
                        for date_field in ['article:published_time', 'datePublished', 'pubdate']:
                            if date_field in metatags:
                                result['date'] = metatags[date_field]
                                break

                    results.append(result)

            return results

        except requests.exceptions.RequestException as e:
            print(f"❌ Google search failed: {e}")
            return []

    def _search_serper(
        self,
        query: str,
        num_results: int,
        language: str,
        time_range: str
    ) -> List[Dict]:
        """Serper API implementation (alternative to Google)"""
        headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }

        payload = {
            'q': query,
            'num': num_results,
            'gl': 'fr' if language == 'fr' else 'us',
            'hl': language
        }

        # Add time range
        if time_range != "any":
            time_map = {'day': 'd', 'week': 'w', 'month': 'm', 'year': 'y'}
            if time_range in time_map:
                payload['tbs'] = f'qdr:{time_map[time_range]}'

        try:
            response = requests.post(
                self.endpoints['serper'],
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            results = []
            if 'organic' in data:
                for idx, item in enumerate(data['organic'], 1):
                    results.append({
                        'title': item.get('title', ''),
                        'url': item.get('link', ''),
                        'snippet': item.get('snippet', ''),
                        'source': self._extract_domain(item.get('link', '')),
                        'date': item.get('date'),
                        'position': idx,
                        'provider': 'serper'
                    })

            return results

        except requests.exceptions.RequestException as e:
            print(f"❌ Serper search failed: {e}")
            return []

    def _search_tavily(
        self,
        query: str,
        num_results: int,
        language: str
    ) -> List[Dict]:
        """Tavily API implementation (alternative)"""
        headers = {
            'Content-Type': 'application/json'
        }

        payload = {
            'api_key': self.api_key,
            'query': query,
            'max_results': num_results,
            'search_depth': 'basic',
            'include_answer': False,
            'include_raw_content': False
        }

        try:
            response = requests.post(
                self.endpoints['tavily'],
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            results = []
            if 'results' in data:
                for idx, item in enumerate(data['results'], 1):
                    results.append({
                        'title': item.get('title', ''),
                        'url': item.get('url', ''),
                        'snippet': item.get('content', ''),
                        'source': self._extract_domain(item.get('url', '')),
                        'score': item.get('score'),
                        'position': idx,
                        'provider': 'tavily'
                    })

            return results

        except requests.exceptions.RequestException as e:
            print(f"❌ Tavily search failed: {e}")
            return []

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        if not url:
            return ""

        # Remove protocol
        domain = url.replace('https://', '').replace('http://', '')

        # Get first part (domain)
        domain = domain.split('/')[0]

        # Remove www.
        domain = domain.replace('www.', '')

        return domain

    def search_with_retry(
        self,
        query: str,
        num_results: int = 5,
        max_retries: int = 3,
        **kwargs
    ) -> List[Dict]:
        """
        Search with retry logic

        Useful for handling rate limits or temporary failures
        """
        for attempt in range(max_retries):
            try:
                results = self.search(query, num_results, **kwargs)
                if results:
                    return results

                # Wait before retry
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff

            except Exception as e:
                print(f"⚠️  Search attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)

        return []

    def format_results(self, results: List[Dict], max_snippet_length: int = 200) -> str:
        """
        Format search results for display

        Args:
            results: Search results
            max_snippet_length: Max length for snippets

        Returns:
            Formatted string
        """
        if not results:
            return "Aucun résultat trouvé."

        output = []
        for i, result in enumerate(results, 1):
            snippet = result['snippet']
            if len(snippet) > max_snippet_length:
                snippet = snippet[:max_snippet_length] + "..."

            output.append(f"{i}. **{result['title']}**")
            output.append(f"   {snippet}")
            output.append(f"   🔗 {result['url']}")

            if result.get('date'):
                output.append(f"   📅 {result['date']}")

            output.append("")

        return "\n".join(output)


# Test function
if __name__ == "__main__":
    # Test with provided Google API credentials
    tool = WebSearchTool(
        provider="google",
        api_key="AIzaSyBwMrXdSmphU4I3J2iE6n7uYyFJnRoLQm8",
        search_engine_id="856c1692fc3734c35"
    )

    print("🔍 Testing Google Custom Search API...\n")

    # Test search
    results = tool.search(
        query="taux de change euro fcfa aujourd'hui",
        num_results=5,
        language="fr"
    )

    print(f"✅ Found {len(results)} results\n")
    print(tool.format_results(results))

    # Test time-restricted search
    print("\n" + "="*60)
    print("🔍 Testing time-restricted search (last week)...\n")

    results = tool.search(
        query="banque afrique crypto monnaie",
        num_results=3,
        language="fr",
        time_range="week"
    )

    print(f"✅ Found {len(results)} results\n")
    print(tool.format_results(results))
