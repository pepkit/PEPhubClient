import os
import json
from typing import Optional, NoReturn, List

import pandas
import peppy
import pandas as pd
import requests
from requests.exceptions import ConnectionError
import urllib3
from peppy import Project
from pydantic.error_wrappers import ValidationError
from ubiquerg import parse_registry_path
from pephubclient.constants import (
    PEPHUB_BASE_URL,
    PEPHUB_PEP_API_BASE_URL,
    RegistryPath,
    ResponseStatusCodes,
)
from pephubclient.models import ProjectDict
from pephubclient.files_manager import FilesManager
from pephubclient.helpers import RequestManager
from pephubclient.exceptions import (
    PEPExistsError,
    IncorrectQueryStringError,
    ResponseError,
)

from pephubclient.pephub_oauth.pephub_oauth import PEPHubAuth
from pephubclient.helpers import MessageHandler

urllib3.disable_warnings()


class PEPHubClient(RequestManager):
    USER_DATA_FILE_NAME = "jwt.txt"
    PATH_TO_FILE_WITH_JWT = (
        os.path.join(os.getenv("HOME"), ".pephubclient/") + USER_DATA_FILE_NAME
    )

    def __init__(self):
        self.registry_path = None

    def login(self) -> NoReturn:
        """
        Log in to PEPhub
        :return: None
        """
        try:
            user_token = PEPHubAuth().login_to_pephub()
        except ConnectionError:
            MessageHandler.print_error("Failed to log in. Connection Error. Try later.")
            return 1

        FilesManager.save_jwt_data_to_file(self.PATH_TO_FILE_WITH_JWT, user_token)

    def logout(self) -> NoReturn:
        """
        Log out from PEPhub
        :return: NoReturn
        """
        FilesManager.delete_file_if_exists(self.PATH_TO_FILE_WITH_JWT)

    def pull(
        self,
        project_registry_path: str,
        project_format: Optional[str] = "default",
        force: Optional[bool] = False
    ) -> None:
        """
        Downl
        :param str project_registry_path: Project registry path in PEPhub (e.g. databio/base:default)
        :param str project_format: project format to be saved. Options: [default, zip]
        :param bool force: if project exists, overwrite it.
        :return: None
        """
        jwt_data = FilesManager.load_jwt_data_from_file(self.PATH_TO_FILE_WITH_JWT)
        try:
            project_dict = self._load_raw_pep(registry_path=project_registry_path, jwt_data=jwt_data)

        except ConnectionError:
            MessageHandler.print_error("Failed to download PEP. Connection Error. Try later.")
            return None

        try:
            self._save_raw_pep(reg_path=project_registry_path, project_dict=project_dict, force=force)
        except PEPExistsError as err:
            MessageHandler.print_warning(f"PEP '{project_registry_path}' already exists. {err}")

    def load_project(
        self,
        project_registry_path: str,
        query_param: Optional[dict] = None,
    ) -> peppy.Project:
        """
        Load peppy project from PEPhub in peppy.Project object
        :param project_registry_path: registry path of the project
        :param query_param: query parameters used in get request
        :return Project: peppy project.
        """
        jwt = FilesManager.load_jwt_data_from_file(self.PATH_TO_FILE_WITH_JWT)
        raw_pep = self._load_raw_pep(project_registry_path, jwt, query_param)
        peppy_project = peppy.Project().from_dict(raw_pep)
        return peppy_project

    def push(
        self,
        cfg: str,
        namespace: str,
        name: Optional[str] = None,
        tag: Optional[str] = None,
        is_private: Optional[bool] = False,
        force: Optional[bool] = False,
    ) -> None:
        """
        Push (upload/update) project to Pephub using config/csv path
        :param str cfg: Project config file (YAML) or sample table (CSV/TSV)
            with one row per sample to constitute project
        :param str namespace: namespace
        :param str name: project name
        :param str tag: project tag
        :param bool is_private: Specifies whether project should be private [Default= False]
        :param bool force: Force push to the database. Use it to update, or upload project. [Default= False]
        :return: None
        """
        peppy_project = peppy.Project(cfg=cfg)

        self.upload(project=peppy_project,
                    namespace=namespace,
                    name=name,
                    tag=tag,
                    is_private=is_private,
                    force=force,)

    def upload(
        self,
        project: peppy.Project,
        namespace: str,
        name: str = None,
        tag: str = None,
        is_private: bool = False,
        force: bool = True,
    ) -> None:
        """
        Upload peppy project to the PEPhub.
        :param peppy.Project project: Project object that has to be uploaded to the DB
        :param namespace: namespace
        :param name: project name
        :param tag: project tag
        :param force: Force push to the database. Use it to update, or upload project.
        :param is_private:
        :param force:
        :return: None
        """
        ...

    @staticmethod
    def _save_raw_pep(
            reg_path: str,
            project_dict: dict,
            force: bool = False,
    ) -> None:
        """

        :param project_dict:
        :param force:
        :return:
        """
        project_name = project_dict["name"]

        config_dict = project_dict.get("_config")
        config_dict["name"] = project_name
        config_dict["description"] = project_dict["description"]
        config_dict['sample_table'] = "sample_table.csv"

        sample_dict = project_dict.get("_sample_dict")
        sample_pandas = pd.DataFrame(sample_dict)

        if project_dict.get("_subsample_dict"):
            subsample_list = [
                pd.DataFrame(sub_a)
                for sub_a in project_dict["_subsample_dict"]
            ]
            config_dict['subsample_table'] = []
            for number, value in enumerate(subsample_list, start=1):
                config_dict['subsample_table'].append(f"subsample_table{number}.csv")
        else:
            subsample_list = None
        reg_path_model = RegistryPath(**parse_registry_path(reg_path))
        folder_path = FilesManager.crete_registry_folder(registry_path=reg_path_model)

        yaml_full_path = os.path.join(folder_path, f"{project_name}_config.yaml")
        sample_full_path = os.path.join(folder_path, config_dict['sample_table'])

        if FilesManager.file_exists(yaml_full_path) or FilesManager.file_exists(sample_full_path):
            if not force:
                raise PEPExistsError

        FilesManager.save_yaml(config_dict, yaml_full_path, force=True)
        FilesManager.save_pandas(sample_pandas, sample_full_path, force=True)

        if config_dict.get('subsample_table'):

            for number, subsample in enumerate(subsample_list):
                FilesManager.save_pandas(subsample,
                                         os.path.join(folder_path, config_dict['subsample_table'][number]),
                                         force=True)

        MessageHandler.print_success(f"Project was downloaded successfully -> {folder_path}")
        return None

    def _load_raw_pep(
        self,
        registry_path: str,
        jwt_data: Optional[str] = None,
        query_param: Optional[dict] = None,
    ) -> dict:
        """
        Request PEPhub and return the requested project as peppy.Project object.

        :param registry_path: Project namespace, eg. "geo/GSE124224:tag"
        :param query_param: Optional variables to be passed to PEPhub
        :param jwt_data: JWT token.

        :return: Raw project in dict.
        """
        if not query_param:
            query_param = {}
        query_param["raw"] = "true"

        self._set_registry_data(registry_path)
        pephub_response = self.send_request(
            method="GET",
            url=self._build_pull_request_url(query_param=query_param),
            headers=self._get_header(jwt_data),
            cookies=None,
        )
        if pephub_response.status_code == 200:
            decoded_response = self._handle_pephub_response(pephub_response)
            correct_proj_dict = ProjectDict(**json.loads(decoded_response))

            # This step is necessary because of this issue: https://github.com/pepkit/pephub/issues/124
            return correct_proj_dict.dict(by_alias=True)

        elif pephub_response.status_code == 404:
            print("File does not exist, or you are unauthorized.")
        elif pephub_response.status_code == 500:
            print("Internal server error.")
        else:
            print(f"Unknown error occurred. Status: {pephub_response.status_code}")

    def _set_registry_data(self, query_string: str) -> None:
        """
        Parse provided query string to extract project name, sample name, etc.

        :param query_string: Passed by user. Contain information needed to locate the project.
        :return: Parsed query string.
        """
        try:
            self.registry_path = RegistryPath(**parse_registry_path(query_string))
        except (ValidationError, TypeError):
            raise IncorrectQueryStringError(query_string=query_string)

    @staticmethod
    def _get_header(jwt_data: Optional[str] = None) -> dict:
        if jwt_data:
            return {"Authorization": jwt_data}
        else:
            return {}

    def _build_pull_request_url(self, query_param: dict = None) -> str:
        if not query_param:
            query_param = {}
        query_param["tag"] = self.registry_path.tag
        endpoint = (
                self.registry_path.namespace
                + "/"
                + self.registry_path.item
        )
        if query_param:
            variables_string = PEPHubClient._parse_query_param(query_param)
            endpoint += variables_string
        return PEPHUB_PEP_API_BASE_URL + endpoint

    @staticmethod
    def _parse_query_param(pep_variables: dict) -> str:
        """
        Grab all the variables passed by user (if any) and parse them to match the format specified
        by PEPhub API for query parameters.

        :return: PEPHubClient variables transformed into string in correct format.
        """
        parsed_variables = []

        for variable_name, variable_value in pep_variables.items():
            parsed_variables.append(f"{variable_name}={variable_value}")
        return "?" + "&".join(parsed_variables)

    @staticmethod
    def _handle_pephub_response(pephub_response: requests.Response):
        decoded_response = PEPHubClient.decode_response(pephub_response)

        if pephub_response.status_code != ResponseStatusCodes.OK_200:
            raise ResponseError(message=json.loads(decoded_response).get("detail"))
        else:
            return decoded_response
