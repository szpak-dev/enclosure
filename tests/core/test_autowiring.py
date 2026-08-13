from enclosure.autowiring import _injectables


def test_discovers_shared_and_app_service_packages() -> None:
    packages = {package.__name__ for package in _injectables}

    assert packages == {
        "enclosure.diagrams.services",
        "enclosure.languages.services",
        "enclosure.records.services",
        "enclosure.projects.services",
        "enclosure.scaffoldings.services",
        "enclosure.shared",
    }
