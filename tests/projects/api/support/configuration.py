BOUNDARIES_YAML = """boundaries:
  tags:
    - name: module
      match: "*"
  flow:
    module_tag: module
    layers: []
    analyzers: []
"""

COMPLETE_BOUNDARIES_YAML = """excluded_patterns:
  - .dev/**
boundaries:
  tags:
    - name: example-module
      match: "*"
    - name: example-entrypoint
      match: app.py
  rules:
    - realm: example-project
      source: example-module
      allow: [example-module]
  flow:
    standalone_tags: [example-entrypoint]
    realms:
      - name: example-project
        module_tag: example-module
    analyzers: []
"""

FLOW_BOUNDARIES_YAML = """boundaries:
  tags:
    - name: example-module
      match: "src/*"
  flow:
    module_tag: example-module
    analyzers: [module-boundaries]
"""

HEALTHY_SHAPE_YAML = """shape:
  realms:
    - name: project
      match: "*"
      shape:
        max_classes_per_file: 1
"""

UNHEALTHY_SHAPE_YAML = """shape:
  realms:
    - name: project
      match: "*"
      shape:
        max_classes_per_file: 0
"""

COMPLETE_SHAPE_YAML = """shape:
  realms:
    - name: example-project
      match: "*"
      excluded_patterns:
        - tests/fixtures/**
      shape:
        max_classes_per_file: 1
"""
