## Help us to help you!

Thank you for taking the time to contribute!

* [Suggesting a feature](#suggesting-a-feature)
* [Filing a bug report](#filing-a-bug-report)
* [Submitting a pull request](#submitting-a-pull-request)

## Suggesting a feature

We can't think of everything. If you've got a good idea for a feature 🚀, then please let us know!

Feature suggestions are embraced, but will often be filed for a rainy day 🌦️. If you require a feature urgently it's best to write it yourself. Don't forget to share 😃

When suggesting a feature, make sure to:

* Check the code on GitHub to make sure it's not already hiding in an unreleased version
* Considered if it's necessary in the library, or is an advanced technique that could be separately explained in an [example](https://granola.readthedocs.io/en/stable/examples/examples_notebooks.html)
* Check existing issues, open and closed, to make sure it hasn't already been suggested

## Filing a bug report

If you're having trouble with GRANOLA and think you have found a bug 🐛, first check out our [issues page](https://github.com/metergroup/GRANOLA/issues) to see if someone else has had a similar issue (open and closed issues). If you can't find anything, and you don't see it in our [docs](https://granola.readthedocs.io/en/stable/), then files an bug report on our issues page. The bug report will walk you through a few questions to give us the needed information to properly diagnose your bug.

## Submitting a pull request

If you've decided to fix a bug, even something as small as a single-letter typo then great! Anything that improves the code/documentation for all future users is warmly welcomed.

If you decide to work on a requested feature it's best to let us (and everyone else) know what you're working on to avoid any duplication of effort. You can do this by replying to the original Issue for the request.

If you want to contribute an example; go for it! We might not always be able to accept your code, but there's a lot to be learned from trying anyway and if you're new to GitHub we're willing to guide you on that journey.

When contributing a new example or making a change to a library please keep your code style consistent with ours. We try to stick to the pep8 guidelines for Python (https://www.python.org/dev/peps/pep-0008/). To ensure this, we run black, isort, and flake8
on all of our main branches.

### Setting up your own fork of this repo.

- On github interface click on `Fork` button.
- Clone your fork of this repo.
    via ssh
    `git clone git@github.com:metergroup/GRANOLA.git`
    via https
    `git clone https://github.com/metergroup/GRANOLA.git`
- Enter the directory `cd granola`
- Add upstream repo `git remote add upstream https://github.com/metergroup/GRANOLA`

### Setting up your own virtual environment

Check which versions of python are currently supported (you can check this in the setup.cfg file, or listed in PyPI). You will need to develop with on of those versions, and when creating a Pull Request, it will test against other versions of python to check for compatibility.

To setup your own virtual environment with your favorite virtual environment tool

- https://virtualenv.pypa.io/en/latest/
- https://docs.python.org/3/library/venv.html
- If you use conda: https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html

Then activate your virtual environment according to the instructions of the tool you are using. That might be:
- `source venv/bin/activate` or `source venv/Script/activate` depending on if you are on a *nix or a Windows system.
- `conda activate {environment name}` if you use conda.
- Something else or something similar to one of the above, check with your tool of choice.

### Install the project in develop mode

Once you have an activated environment, run:

`pip install -r requirements-dev.txt`

This will install all of the development dependencies and as well as install GRANOLA in editable mode in your current environment.

### Run the tests to ensure everything is working

Run `invoke pytest` to run the tests.

### Create a new branch to work on your contribution

Run `git switch -c my_contribution`

### Make your changes

Edit the files using your preferred editor.

### Format the code and lint it (check the style)

Run `invoke style` to format the code and lint it.

### Test your changes

Run `invoke pytest` to run the tests.

Ensure your tests past, and add tests for the new code you add.

### Build the docs locally

Run `invoke docs` to build the docs.

Ensure your new changes are documented.

### Commit your changes

Example: `fix(package): update setup.py arguments 🎉` (emojis are fine too)

### Push your changes to your fork

Run `git push origin my_contribution`

### Submit a pull request

On github interface, click on `Pull Request` button.

Wait CI to run and one of the developers will review your PR.
