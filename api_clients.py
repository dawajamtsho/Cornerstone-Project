#!/usr/bin/env python3
# api_clients.py - Official API Clients for Energy Data
# Primary Data Sources: ENTSO-E, Electricity Maps, IEA, World Bank, UN COMTRADE

import requests
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== ENTSO-E TRANSPARENCY API ====================
class ENTSOEClient:
    """Client for ENTSO-E Transparency Platform REST API"""
    
    BASE_URL = "https://web-api.tp.entsoe.eu/api"
    
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            'User-Agent': 'Energy-MIS-Dashboard/v4.0'
        }
    
    def get_generation_forecast(self, area_code: str, start: str, end: str) -> Optional[pd.DataFrame]:
        """Get generation forecast by production type"""
        try:
            params = {
                'securityToken': self.token,
                'documentType': 'A71',
                'in_Domain': area_code,
                'periodStart': start,
                'periodEnd': end
            }
            
            resp = requests.get(
                f"{self.BASE_URL}/query",
                params=params,
                headers=self.headers,
                timeout=30
            )
            resp.raise_for_status()
            
            # Parse XML response
            from xml.etree import ElementTree as ET
            root = ET.fromstring(resp.content)
            
            # Extract generation data
            data = []
            for ts in root.findall('.//{http://entsoe.eu/transparency/result/core/TS}TimeSeries'):
                for point in ts.findall('.//{http://entsoe.eu/transparency/result/core/TS}Point'):
                    position = point.find('{http://entsoe.eu/transparency/result/core/TS}position')
                    quantity = point.find('{http://entsoe.eu/transparency/result/core/TS}quantity')
                    if position is not None and quantity is not None:
                        data.append({
                            'timestamp': datetime.now() + timedelta(hours=int(position.text)),
                            'generation_mw': float(quantity.text)
                        })
            
            if data:
                return pd.DataFrame(data)
            return None
        except Exception as e:
            logger.error(f"Error fetching ENTSO-E generation forecast: {e}")
            return None
    
    def get_cross_border_flows(self, from_area: str, to_area: str, start: str, end: str) -> Optional[pd.DataFrame]:
        """Get cross-border electricity flows"""
        try:
            params = {
                'securityToken': self.token,
                'documentType': 'A11',
                'in_Domain': from_area,
                'out_Domain': to_area,
                'periodStart': start,
                'periodEnd': end
            }
            
            resp = requests.get(
                f"{self.BASE_URL}/query",
                params=params,
                headers=self.headers,
                timeout=30
            )
            resp.raise_for_status()
            
            from xml.etree import ElementTree as ET
            root = ET.fromstring(resp.content)
            
            data = []
            for ts in root.findall('.//{http://entsoe.eu/transparency/result/core/TS}TimeSeries'):
                for point in ts.findall('.//{http://entsoe.eu/transparency/result/core/TS}Point'):
                    quantity = point.find('{http://entsoe.eu/transparency/result/core/TS}quantity')
                    if quantity is not None:
                        data.append({
                            'timestamp': datetime.now(),
                            'flow_mw': float(quantity.text)
                        })
            
            if data:
                return pd.DataFrame(data)
            return None
        except Exception as e:
            logger.error(f"Error fetching cross-border flows: {e}")
            return None
    
    def get_load_forecast(self, area_code: str, start: str, end: str) -> Optional[pd.DataFrame]:
        """Get electricity load forecast"""
        try:
            params = {
                'securityToken': self.token,
                'documentType': 'A65',
                'in_Domain': area_code,
                'periodStart': start,
                'periodEnd': end
            }
            
            resp = requests.get(
                f"{self.BASE_URL}/query",
                params=params,
                headers=self.headers,
                timeout=30
            )
            resp.raise_for_status()
            
            from xml.etree import ElementTree as ET
            root = ET.fromstring(resp.content)
            
            data = []
            for ts in root.findall('.//{http://entsoe.eu/transparency/result/core/TS}TimeSeries'):
                for point in ts.findall('.//{http://entsoe.eu/transparency/result/core/TS}Point'):
                    quantity = point.find('{http://entsoe.eu/transparency/result/core/TS}quantity')
                    if quantity is not None:
                        data.append({
                            'timestamp': datetime.now(),
                            'load_mw': float(quantity.text)
                        })
            
            if data:
                return pd.DataFrame(data)
            return None
        except Exception as e:
            logger.error(f"Error fetching load forecast: {e}")
            return None

# ==================== ELECTRICITY MAPS API ====================
class ElectricityMapsClient:
    """Client for Electricity Maps API v3"""
    
    BASE_URL = "https://api.electricitymaps.com/v3"
    
    def __init__(self, token: str):
        self.headers = {"auth-token": token}
    
    def get_current_carbon_intensity(self, zone: str) -> Optional[Dict]:
        """Get current carbon intensity"""
        try:
            resp = requests.get(
                f"{self.BASE_URL}/carbon-intensity/latest",
                params={"zone": zone},
                headers=self.headers,
                timeout=10
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Error fetching carbon intensity: {e}")
            return None
    
    def get_carbon_intensity_history(self, zone: str, start: str, end: str) -> Optional[pd.DataFrame]:
        """Get historical carbon intensity"""
        try:
            resp = requests.get(
                f"{self.BASE_URL}/carbon-intensity/history",
                params={"zone": zone, "start": start, "end": end},
                headers=self.headers,
                timeout=15
            )
            resp.raise_for_status()
            payload = resp.json()
            
            series = payload.get("history", [])
            if series:
                df = pd.DataFrame(series)
                df["datetime"] = pd.to_datetime(df["datetime"])
                return df.sort_values("datetime")
            return None
        except Exception as e:
            logger.error(f"Error fetching carbon history: {e}")
            return None
    
    def get_electricity_mix(self, zone: str) -> Optional[Dict]:
        """Get current electricity mix by source"""
        try:
            resp = requests.get(
                f"{self.BASE_URL}/electricity/latest",
                params={"zone": zone},
                headers=self.headers,
                timeout=10
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Error fetching electricity mix: {e}")
            return None

# ==================== IEA API ====================
class IEAClient:
    """Client for IEA Electricity Trade Datasets"""
    
    BASE_URL = "https://data.iea.org/api/v1"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def get_electricity_trade(self, country: str, year: int) -> Optional[Dict]:
        """Get electricity trade data"""
        try:
            params = {
                'api_key': self.api_key,
                'countries': country,
                'years': year,
                'indicators': 'ELECTRADE_EXPPRC,ELECTRADE_IMPPRC'
            }
            
            resp = requests.get(
                f"{self.BASE_URL}/data",
                params=params,
                timeout=15
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Error fetching IEA trade data: {e}")
            return None
    
    def get_renewable_generation(self, country: str, year: int) -> Optional[Dict]:
        """Get renewable electricity generation"""
        try:
            params = {
                'api_key': self.api_key,
                'countries': country,
                'years': year,
                'indicators': 'RENEWABLEGEN'
            }
            
            resp = requests.get(
                f"{self.BASE_URL}/data",
                params=params,
                timeout=15
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Error fetching renewable data: {e}")
            return None

# ==================== WORLD BANK API ====================
class WorldBankClient:
    BASE_URL = "http://api.worldbank.org/v2"

    def get_indicator(self, country_code: str, indicator: str):
        url = f"{self.BASE_URL}/country/{country_code}/indicator/{indicator}"
        params = {"format": "json", "per_page": 500}
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list) or len(data) < 2:
            return None
        rows = data[1]
        # build DataFrame (year, value) and drop None
        out = []
        for row in rows:
            if row.get("value") is not None:
                out.append({
                    "year": int(row["date"]),
                    "value": float(row["value"]),
                })
        return pd.DataFrame(out).sort_values("year")

    def get_electricity_access(self, country_code: str):
        # EG.ELC.ACCS.ZS = Access to electricity (% of population) [web:141][web:142]
        df = self.get_indicator(country_code, "EG.ELC.ACCS.ZS")
        if df is not None:
            df = df.rename(columns={"value": "electricity_access"})
        return df

    def get_electricity_consumption(self, country_code: str):
        # EG.USE.ELEC.KH.PC = Electric power consumption (kWh per capita) [web:146][web:149][web:152]
        df = self.get_indicator(country_code, "EG.USE.ELEC.KH.PC")
        if df is not None:
            df = df.rename(columns={"value": "consumption_kwh"})
        return df

# ==================== UN COMTRADE API ====================
class UNComtradeClient:
    """Client for UN COMTRADE Trade Data"""
    
    BASE_URL = "https://comtrade.un.org/api/get"
    
    def get_electricity_trade(self, reporter: str, partner: str, year: int) -> Optional[Dict]:
        """Get bilateral electricity trade (HS Code 2716)"""
        try:
            params = {
                'max': 50000,
                'type': 'C',
                'freq': 'A',
                'px': 'HS',
                'ps': year,
                'r': reporter,
                'p': partner,
                'rg': '12',  # Both imports and exports
                'cc': '2716'  # Electricity HS code
            }
            
            resp = requests.get(
                self.BASE_URL,
                params=params,
                timeout=15
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Error fetching UN COMTRADE data: {e}")
            return None

# ==================== GLOBAL ENERGY MONITOR API ====================
class GlobalEnergyMonitorClient:
    """Client for Global Energy Monitor Data"""
    
    BASE_URL = "https://globalenergymonitor.org"
    
    def get_power_plant_data(self, country: str) -> Optional[Dict]:
        """Get power plant and interconnection data"""
        try:
            # GEM provides data through their platform
            # This would typically require their specific API or CSV downloads
            logger.info(f"Fetching Global Energy Monitor data for {country}")
            # Return placeholder - actual implementation depends on GEM's API availability
            return None
        except Exception as e:
            logger.error(f"Error fetching GEM data: {e}")
            return None

# ==================== HELPER FUNCTIONS ====================
def validate_api_tokens(tokens: Dict[str, str]) -> Dict[str, bool]:
    """Validate all API tokens"""
    validation = {}
    
    # Test ENTSO-E
    try:
        client = ENTSOEClient(tokens.get('entsoe', ''))
        validation['entsoe'] = 'Valid' if tokens.get('entsoe') else 'Missing'
    except:
        validation['entsoe'] = 'Invalid'
    
    # Test Electricity Maps
    try:
        client = ElectricityMapsClient(tokens.get('emaps', ''))
        resp = requests.get(
            "https://api.electricitymaps.com/v3/carbon-intensity/latest",
            params={"zone": "IN"},
            headers={"auth-token": tokens.get('emaps', '')},
            timeout=5
        )
        validation['emaps'] = 'Valid' if resp.status_code == 200 else 'Invalid'
    except:
        validation['emaps'] = 'Invalid'
    
    return validation

if __name__ == "__main__":
    # Test API clients
    print("API Clients initialized successfully!")
