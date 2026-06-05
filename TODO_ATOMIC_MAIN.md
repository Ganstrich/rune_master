# Refactoring Plan: Making `main.py` Atomic

This plan outlines the steps required to split `main.py` into smaller, highly modular, and easily testable components. The goal is to separate concerns and leave `main.py` as a lightweight entry point/CLI controller.

---

## 🛠️ Step-by-Step Action Items

### Phase 1: Move Data & Caching Helpers
Currently, caching logic (`_cache_equipment_resources`) is mixed inside `main.py`.

- [ ] **Task 1.1: Relocate `_cache_equipment_resources`**
  - Move the helper function to `data/cache_manager.py` or a dedicated data utility.
  - Expose a clean interface like `CacheManager.cache_resources(equipments, api)` or similar.
- [ ] **Task 1.2: Update imports and call site**
  - Update `main.py` to import and call this relocated function.
  - Verify that the equipment loading step still works properly.

---

### Phase 2: Decouple the Web Server
The built-in HTTP server has unique dependencies and logic that can be isolated.

- [ ] **Task 2.1: Create `web_server.py`**
  - Create a new module `web_server.py` in the root (or under a new utility folder).
  - Move `QuietHTTPRequestHandler` and `start_server` to this module.
- [ ] **Task 2.2: Export server runner**
  - Expose a simple `start_dev_server(port, directory)` function.
- [ ] **Task 2.3: Integrate in `main.py`**
  - Import and call `start_dev_server` from `main.py`.

---

### Phase 3: Move CLI Configuration Mapping
Building `ProcessingConfig` manually from CLI options is verbose and clutters `main.py`.

- [ ] **Task 3.1: Create configuration factory**
  - Move the logic that maps CLI arguments (`argparse.Namespace`) to `ProcessingConfig` into a helper module (e.g., `models/processing_config.py` as a static method/factory, or `config_factory.py`).
  - Example: `ProcessingConfig.from_args(args, config_defaults)`
- [ ] **Task 3.2: Clean up argument parsing in `main.py`**
  - Keep only the `argparse` setup in `main.py` and pass the parsed `args` directly to the factory method.

---

### Phase 4: Extract the Orchestration Pipeline
The execution steps (`load_equipment`, `process_equipment`, `generate_visualizations`) represent the business logic of the pipeline.

- [ ] **Task 4.1: Create `pipeline.py`**
  - Define a runner or functions in `pipeline.py` to orchestrate these high-level steps.
  - Example workflow:
    ```python
    def run_pipeline(config: ProcessingConfig, tune: bool = False, output_dir: str = "visualizations"):
        equipments, cache, api = load_equipment(config)
        groups = process_equipment(equipments, config, cache, api, tune)
        if not groups:
            raise ValueError("No groups generated")
        index_path = generate_visualizations(groups, output_dir)
        return index_path
    ```
- [ ] **Task 4.2: Move pipeline logic**
  - Relocate the actual functions (`load_equipment`, `process_equipment`, `generate_visualizations`) from `main.py` into `pipeline.py`.

---

### Phase 5: Streamline `main.py`
Finally, thin out the entry point file.

- [ ] **Task 5.1: Clean up `main.py` imports**
  - Remove all unused imports (e.g., `time`, model classes, api classes, server classes).
- [ ] **Task 5.2: Simplify `main()`**
  - Reduce `main()` to:
    1. Parse CLI arguments.
    2. Build/get `ProcessingConfig`.
    3. Run the pipeline from `pipeline.py`.
    4. Start the server (if requested).
- [ ] **Task 5.3: Verify and Test**
  - Run the CLI command with all supported arguments to verify that everything still works seamlessly.
