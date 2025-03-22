from .utils import *

import os
import json
import requests
import time
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs


class PluginSettings:
    def __init__(self):
        self.addon = xbmcaddon.Addon(id='plugin.program.steamgames')
        self.library_cache = self.addon.getSetting('library_cache')
        self.nfo_path = self.addon.getSetting('nfo_files')
        self.steam_user_id = self.addon.getSetting('steam_user_id')
        self.steam_api_key = self.addon.getSetting('steam_api_key')

        if not self.steam_user_id or not self.steam_api_key:
            self.show_error("Erro: Steam User ID ou API Key não configurados corretamente.")
            sys.exit(1)

        if not self.library_cache or not xbmcvfs.exists(self.library_cache):
            self.show_error("Erro: Caminho do Library Cache inválido ou não configurado.")
            sys.exit(1)

    def show_error(self, message):
        dialog = xbmcgui.Dialog()
        dialog.notification("Erro", message, xbmcgui.NOTIFICATION_ERROR, 5000)

class SteamAPI:
    def __init__(self, steam_user_id, steam_api_key):
        self.addon = xbmcaddon.Addon(id='plugin.program.steamgames')
        self.library_cache = self.addon.getSetting('library_cache')
        self.steam_grid = self.addon.getSetting('steam_grid')
        self.steam_user_id = steam_user_id
        self.steam_api_key = steam_api_key
        self.api_url_owned_games = "http://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
        self.assets_dir = xbmcvfs.translatePath('special://userdata/addon_data/plugin.program.steamgames/assets/')
        self.json_dir = xbmcvfs.translatePath('special://userdata/addon_data/plugin.program.steamgames/')

    def get_owned_games(self):
        params = {
            'steamid': self.steam_user_id,
            'key': self.steam_api_key,
            'format': 'json',
            'include_appinfo': 'true'
        }

        dialog_progress = xbmcgui.DialogProgress()
        dialog_progress.create("Buscando jogos", "Por favor, aguarde enquanto buscamos os jogos...")

        try:
            response = requests.get(self.api_url_owned_games, params=params)
            response.raise_for_status()
            data = response.json()

            if 'response' in data and 'games' in data['response']:
                games = data['response']['games']
                total_games = len(games)

                for i, game in enumerate(games):
                    game_name = game.get('name', f"Game_{game['appid']}")
                    game['name'] = game_name
                    
                    time.sleep(0.2)
                    
                    dialog_progress.update(int((i / total_games) * 100),
                                           f"Atualizando sua lista de jogos: {game_name} {i + 1} de {total_games}")

                    # Obter imagens do diretório library_cache
                    appid = game['appid']
                    image_paths = self.get_images_from_library_cache(appid)

                    # Definir os valores de capsule, hero, logo, header, icon com os valores encontrados em library_cache
                    game['capsule'] = image_paths.get('capsule', None)
                    game['hero'] = image_paths.get('hero', None)
                    game['logo'] = image_paths.get('logo', None)
                    game['header'] = image_paths.get('header', None)
                    game['icon'] = image_paths.get('icon', None)
                    game['tags'] = {}

                    # Agora substituir os valores com imagens do steam_grid, se encontradas
                    steam_grid_images = self.get_steam_grid_images(appid)
                    game['capsule'] = steam_grid_images.get('steam_grid_p', game.get('capsule', None))
                    game['hero'] = steam_grid_images.get('steam_grid__hero', game.get('hero', None))
                    game['logo'] = steam_grid_images.get('steam_grid__logo', game.get('logo', None))

                    # Caso a imagem no steam_grid não seja encontrada, o valor original de library_cache é mantido
                    if not steam_grid_images.get('steam_grid_p'):
                        game['capsule'] = game.get('capsule', None)
                    if not steam_grid_images.get('steam_grid__hero'):
                        game['hero'] = game.get('hero', None)
                    if not steam_grid_images.get('steam_grid__logo'):
                        game['logo'] = game.get('logo', None)

                    if dialog_progress.iscanceled():
                        dialog_progress.close()
                        return None

                dialog_progress.close()
                return games
            else:
                raise ValueError("A resposta da Steam não contém jogos válidos.")
        except requests.exceptions.RequestException as e:
            dialog = xbmcgui.Dialog()
            dialog.notification("Erro", f"Falha na requisição: {str(e)}", xbmcgui.NOTIFICATION_ERROR, 5000)
            dialog_progress.close()
            return None

    def get_steam_grid_images(self, appid):
        """Procura imagens na pasta steam_grid que correspondam ao appid."""
        
        # Obtém o caminho configurado para a pasta steam_grid
        image_types = ['p', '_logo', '_hero']
        image_paths = {}

        for image_type in image_types:
            file_path = os.path.join(self.steam_grid, f"{appid}{image_type}.jpg")
            
            if xbmcvfs.exists(file_path):
                image_paths[f"steam_grid_{image_type}"] = self.to_special_path(file_path)
            
            else:
                # Verificar outras extensões comuns
                for ext in ['.png', '.jpeg', '.bmp', '.gif']:
                    alternate_path = file_path.replace('.jpg', ext)
                    if xbmcvfs.exists(alternate_path):
                        image_paths[f"steam_grid_{image_type}"] = self.to_special_path(alternate_path)
                        break

        return image_paths

    def get_images_from_library_cache(self, appid):
        """Busca as imagens de um jogo no diretório Library Cache, caso não encontre na steam_grid."""
        image_types = {
            "header": f"{appid}_header.jpg",
            "capsule": f"{appid}_library_600x900.jpg",
            "hero": f"{appid}_library_hero.jpg",
            "logo": f"{appid}_logo.png",
            "icon": f"{appid}_icon.jpg"
        }

        image_paths = {}
        for image_type, filename in image_types.items():
            file_path_cache = os.path.join(self.library_cache, filename)
            if xbmcvfs.exists(file_path_cache):
                image_paths[image_type] = self.to_special_path(file_path_cache)
            else:
                image_paths[image_type] = None

        return image_paths

    def to_special_path(self, file_path):
        return file_path.replace(xbmcvfs.translatePath('special://userdata/'), 'special://userdata/')


class GameSaver:
    def __init__(self):
        self.save_json_path = xbmcvfs.translatePath('special://userdata/addon_data/plugin.program.steamgames/')

    def save_games(self, games):
        """
        Salva os jogos Steam em um arquivo JSON, completando os dados com informações dos arquivos NFO.
        """
        if not games:
            return

        if not xbmcvfs.exists(self.save_json_path):
            xbmcvfs.mkdirs(self.save_json_path)

        file_path = os.path.join(self.save_json_path, "steam_games.json")
        nfo_path = PluginSettings().nfo_path  # Obtém o caminho configurado para os NFOs

        steam_games = {}
        for idx, game in enumerate(games):
            game_data = {
                "appid": game.get("appid"),
                "appName": game.get("name", ""),
                "LastPlayTime": game.get("rtime_last_played", ""),
                "capsule": game.get("capsule"),
                "icon": game.get("icon"),
                "hero": game.get("hero"),
                "logo": game.get("logo"),
                "header": game.get("header"),
                "tags": game.get("tags", {})
            }

            # Verifica e lê o arquivo .nfo correspondente
            if nfo_path:
                nfo_file = os.path.join(nfo_path, f"{game_data['appName']}.nfo")
                nfo_data = read_nfo_data(nfo_file)
                game_data.update(nfo_data)

            steam_games[str(idx)] = game_data

        # Salva o JSON atualizado
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({"steam": steam_games}, f, ensure_ascii=False, indent=4)

        xbmcgui.Dialog().notification("Sucesso", "Jogos Steam salvos com sucesso.", xbmcgui.NOTIFICATION_INFO, 5000)




