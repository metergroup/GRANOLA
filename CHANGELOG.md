# Change Log

## Unreleased

### Highlights

<!-- Include any especially major or disruptive changes here -->

### Bugfixes

<!-- Bugfixes for the GRANOLA code base -->

### Configuration

<!-- Changes to how GRANOLA can be configured -->

### Depreciation

<!-- Changes to how GRANOLA code that deprecates previous code or behvior -->

### Documentation

<!-- Major changes to documentation and policies. Small docs changes
     don't need a changelog entry. -->

### Feature

<!-- New Features added to GRANOLA -->

### Packaging

<!-- Changes to how GRANOLA is packaged, such as dependency requirements -->

### Refactor

<!-- Changes to how GRANOLA code with not changes to behavior -->

### Removals

<!-- BREAKING changes of code or behavior in GRANOLA-->


## 0.9.0.rc1

### Highlights

- See https://granola.readthedocs.io/en/stable/config/moving_to_v0_9_0.html for more information on migrating from previous versions to 0.9.0
- Deprecated MockSerial in favor of new Cereal class.

### Bugfixes

<!-- Bugfixes for the GRANOLA code base -->

### Configuration

- Added ability to pass any custom Hook or CommandReader into configuration as strings as long as they are defined imported somewhere by the time ``Cereal`` is initialized.
- Added ability to initialize ``CannedQueries`` with dictionary of serial commands
instead of file paths, or a mixture of both.
- Changed many aspects of the configuration syntax
    - See https://granola.readthedocs.io/en/stable/config/moving_to_v0_9_0.html for more information

### Depreciation

- Deprecated MockSerial class in favor of [Cereal](https://granola.readthedocs.io/en/stable/bk_cereal.html) class.
- Deprecated how MockSerial configuration is handled when moving to Cereal.
    - See https://granola.readthedocs.io/en/stable/config/moving_to_v0_9_0.html for more information on migrating from previous versions to 0.9.0

### Documentation

- Added a readthedocs website at https://granola.readthedocs.io/en/stable/
- Added API, configuration, and examples to readthedocs
### Feature

- Add a write_terminator parameter that lets you specify your end-of-line character.

### Packaging

- Added black, isort, and invoke to requirements

### Refactor

- Reformatted code with black and isort
    - Added black and isort checks in CI build

### Removals

<!-- BREAKING changes of code or behavior in GRANOLA-->