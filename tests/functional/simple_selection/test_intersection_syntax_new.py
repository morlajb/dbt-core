import os
import pytest

from dbt.tests.util import run_dbt, run_sql_file
from dbt.tests.tables import get_tables_in_schema
from tests.functional.simple_selection.test_graph_select import models  # noqa


selectors_yml = """
            selectors:
            - name: same_intersection
              definition:
                intersection:
                  - fqn: users
                  - fqn:users
            - name: tags_intersection
              definition:
                intersection:
                  - tag: bi
                  - tag: users
            - name: triple_descending
              definition:
                intersection:
                  - fqn: "*"
                  - tag: bi
                  - tag: users
            - name: triple_ascending
              definition:
                intersection:
                  - tag: users
                  - tag: bi
                  - fqn: "*"
            - name: intersection_with_exclusion
              definition:
                intersection:
                  - method: fqn
                    value: users_rollup_dependency
                    parents: true
                  - method: fqn
                    value: users
                    children: true
                  - exclude:
                    - users_rollup_dependency
            - name: intersection_exclude_intersection
              definition:
                intersection:
                  - tag:bi
                  - "@users"
                  - exclude:
                      - intersection:
                        - tag:bi
                        - method: fqn
                          value: users_rollup
                          children: true
            - name: intersection_exclude_intersection_lack
              definition:
                intersection:
                  - tag:bi
                  - "@users"
                  - exclude:
                      - intersection:
                        - method: fqn
                          value: emails
                          children_parents: true
                        - method: fqn
                          value: emails_alt
                          children_parents: true
        """


@pytest.fixture
def selectors():
    return selectors_yml


@pytest.fixture
def create_tables(test_data_dir, unique_schema):
    path = os.path.join(test_data_dir, "seed.sql")
    run_sql_file(path, unique_schema)


def verify_selected_users(project, results):
    # users
    assert len(results) == 1

    created_models = get_tables_in_schema(project.test_schema)
    assert "users" in created_models
    assert "users_rollup" not in created_models
    assert "emails_alt" not in created_models
    assert "subdir" not in created_models
    assert "nested_users" not in created_models


def test__postgres__same_model_intersection(project, create_tables):

    results = run_dbt(["run", "--models", "users,users"])
    verify_selected_users(project, results)


def test__postgres__same_model_intersection_selectors(project, create_tables):

    results = run_dbt(["run", "--selector", "same_intersection"])
    verify_selected_users(project, results)


def test__postgres__tags_intersection(project, create_tables):

    results = run_dbt(["run", "--models", "tag:bi,tag:users"])
    verify_selected_users(project, results)


def test__postgres__tags_intersection_selectors(project, create_tables):

    results = run_dbt(["run", "--selector", "tags_intersection"])
    verify_selected_users(project, results)


def test__postgres__intersection_triple_descending(project, create_tables):

    results = run_dbt(["run", "--models", "*,tag:bi,tag:users"])
    verify_selected_users(project, results)


def test__postgres__intersection_triple_descending_schema(project, create_tables):

    results = run_dbt(["run", "--models", "*,tag:bi,tag:users"])
    verify_selected_users(project, results)


def test__postgres__intersection_triple_descending_schema_selectors(project, create_tables):

    results = run_dbt(["run", "--selector", "triple_descending"])
    verify_selected_users(project, results)


def test__postgres__intersection_triple_ascending(project, create_tables):

    results = run_dbt(["run", "--models", "tag:users,tag:bi,*"])
    verify_selected_users(project, results)


def test__postgres__intersection_triple_ascending_schema_selectors(project, create_tables):

    results = run_dbt(["run", "--selector", "triple_ascending"])
    verify_selected_users(project, results)


def verify_selected_users_and_rollup(project, results):
    # users, users_rollup
    assert len(results) == 2

    created_models = get_tables_in_schema(project.test_schema)
    assert "users" in created_models
    assert "users_rollup" in created_models
    assert "emails_alt" not in created_models
    assert "subdir" not in created_models
    assert "nested_users" not in created_models


def test__postgres__intersection_with_exclusion(project, create_tables):

    results = run_dbt(
        [
            "run",
            "--models",
            "+users_rollup_dependency,users+",
            "--exclude",
            "users_rollup_dependency",
        ]
    )
    verify_selected_users_and_rollup(project, results)


def test__postgres__intersection_with_exclusion_selectors(project, create_tables):

    results = run_dbt(["run", "--selector", "intersection_with_exclusion"])
    verify_selected_users_and_rollup(project, results)


def test__postgres__intersection_exclude_intersection(project, create_tables):

    results = run_dbt(["run", "--models", "tag:bi,@users", "--exclude", "tag:bi,users_rollup+"])
    verify_selected_users(project, results)


def test__postgres__intersection_exclude_intersection_selectors(project, create_tables):

    results = run_dbt(["run", "--selector", "intersection_exclude_intersection"])
    verify_selected_users(project, results)


def test__postgres__intersection_exclude_intersection_lack(project, create_tables):

    results = run_dbt(["run", "--models", "tag:bi,@users", "--exclude", "@emails,@emails_alt"])
    verify_selected_users_and_rollup(project, results)


def test__postgres__intersection_exclude_intersection_lack_selector(project, create_tables):

    results = run_dbt(["run", "--selector", "intersection_exclude_intersection_lack"])
    verify_selected_users_and_rollup(project, results)


def test__postgres__intersection_exclude_triple_intersection(project, create_tables):

    results = run_dbt(["run", "--models", "tag:bi,@users", "--exclude", "*,tag:bi,users_rollup"])
    verify_selected_users(project, results)


def test__postgres__intersection_concat(project, create_tables):

    results = run_dbt(["run", "--models", "tag:bi,@users", "emails_alt"])
    # users, users_rollup, emails_alt
    assert len(results) == 3

    created_models = get_tables_in_schema(project.test_schema)
    assert "users" in created_models
    assert "users_rollup" in created_models
    assert "emails_alt" in created_models
    assert "subdir" not in created_models
    assert "nested_users" not in created_models


def test__postgres__intersection_concat_intersection(project, create_tables):

    results = run_dbt(["run", "--models", "tag:bi,@users", "@emails_alt,emails_alt"])
    # users, users_rollup, emails_alt
    assert len(results) == 3

    created_models = get_tables_in_schema(project.test_schema)
    assert "users" in created_models
    assert "users_rollup" in created_models
    assert "emails_alt" in created_models
    assert "subdir" not in created_models
    assert "nested_users" not in created_models


def test__postgres__intersection_concat_exclude(project, create_tables):

    results = run_dbt(
        ["run", "--models", "tag:bi,@users", "emails_alt", "--exclude", "users_rollup"]
    )
    # users, emails_alt
    assert len(results) == 2

    created_models = get_tables_in_schema(project.test_schema)
    assert "users" in created_models
    assert "emails_alt" in created_models
    assert "users_rollup" not in created_models
    assert "subdir" not in created_models
    assert "nested_users" not in created_models


def test__postgres__intersection_concat_exclude_concat(project, create_tables):

    results = run_dbt(
        [
            "run",
            "--models",
            "tag:bi,@users",
            "emails_alt,@users",
            "--exclude",
            "users_rollup_dependency",
            "users_rollup",
        ]
    )
    # users, emails_alt
    assert len(results) == 2

    created_models = get_tables_in_schema(project.test_schema)
    assert "users" in created_models
    assert "emails_alt" in created_models
    assert "users_rollup" not in created_models
    assert "subdir" not in created_models
    assert "nested_users" not in created_models


def test__postgres__intersection_concat_exclude_intersection_concat(project, create_tables):

    results = run_dbt(
        [
            "run",
            "--models",
            "tag:bi,@users",
            "emails_alt,@users",
            "--exclude",
            "@users,users_rollup_dependency",
            "@users,users_rollup",
        ]
    )
    # users, emails_alt
    assert len(results) == 2

    created_models = get_tables_in_schema(project.test_schema)
    assert "users" in created_models
    assert "emails_alt" in created_models
    assert "users_rollup" not in created_models
    assert "subdir" not in created_models
    assert "nested_users" not in created_models
