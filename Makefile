poetry:
	sed -i .bak "s|\$${NEXUS_URL}|${NEXUS_URL}|g; s|\$${NEXUS_HOST}|${NEXUS_URL}|g;" pyproject.toml
	-poetry update
	-poetry install
	mv pyproject.toml.bak pyproject.toml