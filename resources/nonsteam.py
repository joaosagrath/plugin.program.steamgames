from .utils import *

import os
import json
import configparser
import struct
import xbmcaddon
import xbmcgui
import xbmcvfs
import time

class NonSteam:
    """
    Classe para sincronização e manipulação de jogos Non-Steam.
    """

    @staticmethod
    def read_url_from_shortcut(file_path):
        """
        Lê a URL de um arquivo .url.
        """
        config = configparser.ConfigParser()
        config.read(file_path)
        if 'InternetShortcut' in config:
            return config['InternetShortcut'].get('URL')
        return None
        
    @staticmethod
    def get_steam_grid_path():
        """
        Obtém o caminho para o diretório Steam Grid a partir das configurações do addon.
        """
        addon = xbmcaddon.Addon()
        steam_grid_path = addon.getSetting('steam_grid')
        return steam_grid_path
        

    @staticmethod
    def get_valid_image_extension(file_path):
        """
        Verifica as extensões de imagem mais comuns e retorna a extensão válida para cada tipo de arte.
        Para cada tipo de arte (poster, logo, hero, header), verifica a existência da extensão.
        Retorna uma tupla contendo a extensão para cada tipo de arte.
        """
        valid_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif']
        
        # Inicializa os valores de cada tipo de arte
        poster_ext = None
        logo_ext = None
        hero_ext = None
        header_ext = None

        for ext in valid_extensions:
            # Verifica cada tipo de arte separadamente
            if os.path.exists(f"{file_path}p{ext}"):
                poster_ext = ext
            if os.path.exists(f"{file_path}_logo{ext}"):
                logo_ext = ext    
            if os.path.exists(f"{file_path}_hero{ext}"):
                hero_ext = ext    
            if os.path.exists(f"{file_path}{ext}"):
                header_ext = ext
        
        return poster_ext, logo_ext, hero_ext, header_ext  # Retorna as extensões encontradas
    
    def sync_non_steam_games(self):
        """
        Sincroniza jogos Non-Steam a partir de atalhos e arquivos .url, exibindo barra de progresso.
        Gera um JSON com a estrutura padronizada solicitada, incluindo a padronização dos campos de arte.
        """
        addon = xbmcaddon.Addon()
        shortcuts_vdf_path = addon.getSetting('shortcuts_vdf')
        non_steam_url_path = addon.getSetting('non-steam_url')

        # Verifica se os caminhos configurados existem
        if not os.path.exists(shortcuts_vdf_path):
            xbmcgui.Dialog().ok("Erro", f"Arquivo não encontrado: {shortcuts_vdf_path}")
            return

        if not os.path.isdir(non_steam_url_path):
            xbmcgui.Dialog().ok("Erro", f"Diretório não encontrado: {non_steam_url_path}")
            return

        try:
            # Lê e processa o arquivo shortcuts.vdf
            shortcuts = self.parse_shortcuts(shortcuts_vdf_path)

            # Prepare a barra de progresso
            dialog_progress = xbmcgui.DialogProgress()
            dialog_progress.create("Sincronizando Jogos", "Iniciando...")

            total_shortcuts = len(shortcuts.get('shortcuts', {}))
            processed_count = 0

            # Nova estrutura no formato solicitado
            non_steam_games = {}

            # Obtém o diretório Steam Grid
            steam_grid = self.get_steam_grid_path()

            # Processa cada jogo e organiza no formato solicitado
            for idx, (shortcut_id, shortcut_data) in enumerate(shortcuts.get('shortcuts', {}).items()):
                app_name = shortcut_data.get('appName', '')

                # Inicializa os campos do jogo
                game_data = {
                    "appid": shortcut_data.get('appid', ""),
                    "appName": app_name,
                    "LastPlayTime": shortcut_data.get('LastPlayTime', ""),
                    "capsule": "",  # Antes "poster"
                    "icon": "",  # Novo campo
                    "logo": "",
                    "hero": "",
                    "header": "",
                    "tags": shortcut_data.get('tags', {})
                }

                # Atualiza caminhos de imagens com base no Steam Grid
                if steam_grid:
                    appid = shortcut_data.get('appid', '')
                    poster_ext, logo_ext, hero_ext, header_ext = self.get_valid_image_extension(os.path.join(steam_grid, str(appid)))

                    if poster_ext:
                        game_data['capsule'] = os.path.join(steam_grid, f"{appid}p{poster_ext}")  # Renomeado de poster para capsule
                    if logo_ext:
                        game_data['logo'] = os.path.join(steam_grid, f"{appid}_logo{logo_ext}")
                    if hero_ext:
                        game_data['hero'] = os.path.join(steam_grid, f"{appid}_hero{hero_ext}")
                    if header_ext:
                        game_data['header'] = os.path.join(steam_grid, f"{appid}{header_ext}")
                    
                    # Define o caminho do ícone como o mesmo que header, se aplicável (ou pode ser customizado)
                    game_data['icon'] = game_data['header']

                # Obtém o appid de arquivos .url, caso não exista no atalho
                url_file_path = os.path.join(non_steam_url_path, f"{app_name}.url")
                if os.path.exists(url_file_path):
                    url = self.read_url_from_shortcut(url_file_path)
                    if url and "steam://rungameid/" in url:
                        appid_value = url.split("steam://rungameid/")[-1]
                        game_data['appid'] = appid_value

                # Adiciona o jogo ao dicionário final
                non_steam_games[str(idx)] = game_data

                # Atualiza a barra de progresso com o nome do jogo
                processed_count += 1
                dialog_progress.update(
                    int((processed_count / total_shortcuts) * 100),
                    f"Processando: {app_name}"
                )

                time.sleep(0.2)  # Simula processamento para melhor UX

                # Verifica se o usuário cancelou a operação
                if dialog_progress.iscanceled():
                    xbmcgui.Dialog().ok("Cancelado", "A sincronização foi cancelada.")
                    return

            dialog_progress.close()

            # Define o caminho para salvar o arquivo JSON
            special_path = xbmcvfs.translatePath('special://userdata/addon_data/plugin.program.steamgames/')
            updated_output_path = os.path.join(special_path, 'non_steam_games.json')

            # Salva o JSON estruturado
            with open(updated_output_path, 'w', encoding='utf-8') as f:
                json.dump({"non_steam": non_steam_games}, f, indent=4, ensure_ascii=False)

            # Exibe o diálogo de sucesso após o término do processo
            xbmcgui.Dialog().ok("Sucesso", f"Jogos Non-Steam atualizados com sucesso!\nArquivo gerado em: {updated_output_path}")

        except Exception as e:
            xbmcgui.Dialog().ok("Erro", f"Erro ao processar o arquivo: {str(e)}")



      
    @staticmethod
    def parse_shortcuts(filename):
        """
        Lê e converte o arquivo shortcuts.vdf para um dicionário.
        """
        with open(filename, "rb") as infile:
            return NonSteam._read_dict(infile)

    @staticmethod
    def _read_int(infile):
        return struct.unpack("I", infile.read(4))[0]

    @staticmethod
    def _read_long(infile):
        return struct.unpack("Q", infile.read(8))[0]

    @staticmethod
    def _read_str(infile):
        res = []
        while True:
            peek = infile.peek()
            length = peek.find(b'\x00')
            if length > -1:
                res.append(infile.read(length + 1))
                try:
                    return b''.join(res)[:-1].decode("utf8")
                except UnicodeDecodeError:
                    return b''.join(res)[:-1].decode("latin1")
            res.append(infile.read(len(peek)))

    @staticmethod
    def _read_dict(infile):
        res = {}
        while True:
            dtype = infile.read(1)
            if dtype == b'\x08':  # End of dictionary
                break
            name = NonSteam._read_str(infile)
            if dtype == b'\x00':
                value = NonSteam._read_dict(infile)
            elif dtype == b'\x01':
                value = NonSteam._read_str(infile)
            elif dtype == b'\x02':
                value = NonSteam._read_int(infile)
            elif dtype == b'\x07':
                value = NonSteam._read_long(infile)
            else:
                raise ValueError("Tipo desconhecido")
            res[name] = value
        return res
