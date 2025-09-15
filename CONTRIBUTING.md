# Contributing to Awesome European OpenSource

**Thanks for taking the time to contribute! ❤️**

Before you start please read our [CODE OF CONDUCT](https://github.com/european-opensource/awesome-european-opensource/blob/main/CODE_OF_CONDUCT.md) so that you can understand what actions will and will not be tolerated.

All types of contributions are encouraged and valued, no matter if it's a bug report, a feature request, or a Pull Request.

## How to Contribute

- **🚀 I want to submit a project**: [Fill out the form](https://awesome-european-opensource/form)
- **❓ I have a question:** Ask in [Open an Issue](https://github.com/European-OpenSource/awesome-european-opensource/issues/new?template=QUESTION.yml)
- **🐛 I found a bug:** [Open an Issue](https://github.com/European-OpenSource/awesome-european-opensource/issues/new?template=BUG_REPORT.yml)
- **💡 I have an idea:** [Open an Issue](https://github.com/European-OpenSource/awesome-european-opensource/issues/new?template=FEATURE_REQUEST.yml)
- **💻 I want to code (or improve documentation):** See [Contributing code](#contributing-code) section

## Contributing Code

> ⚠️ **Important:** If you're looking to add a new feature, please check if a feature issue exists or create one before starting development.

When you've identified an issue and you want to work on it here's how you can get started:

1. Fork the repo
2. Setup project
   - If you using VS Code: Open the project in devcontainer mode
   - Or, setup your local env with `just setup`
3. Add your changes
4. Test your changes using `just lint` and `just -- import --csv imports/<filename.csv>` to make sure everything still works
5. Commit & push your changes (we suggest use a feature or fix branch)
6. Open a PR to get your changes merged.

### With Dev Container (Recommended)

1. Requirements: `Docker >=24`
2. Open the project in Visual Studio Code
3. Install the Dev Containers extension
4. Reopen in container when prompted

### Without Dev Container

1. **Requirements**

   | pkg    | version  |
   | ------ | -------- |
   | Docker | `>=24`   |
   | Python | `>=3.12` |

2. **Check the project:**

   ```bash
   just setup
   ```

### PR Guidelines

- Keep PRs focused on a single feature/fix
- Include tests for new functionality
- Update documentation if needed
- Ensure all CI checks pass

### Code Style Guidelines

- Follow existing code patterns and conventions
- Use meaningful variable and function names
- Add comments for complex logic
- Keep functions small and focused
- Follow the project's ESLint configuration

### How to add new project

1. Download csv from [tally.so](https://tally.so)
2. Save csv file into `imports/` directory (if doesn't exist create it)
3. Execute `just import --csv imports/<filename>`
4. Check and validate the output
5. Create a pull-request (It would be better to create a single MR for each project.)

   ```bash
   git checkout -b feat/import-projects-$(date +%m-%d-%Y-%s)
   git add .
   just test
   git commit -m "feat(awesome:projects): import projects"
   ```
6. When the pull request is closed, the workflow [sync-europeanopensource-eu.yml](.github/workflows/sync-europeanopensource-eu.yml) is triggered, which in turn activates a specific workflow on the [europeanopensource.eu](https://github.com/European-OpenSource/europeanopensource.eu) repository.

## Join our Community

[![LinkedIn](https://img.shields.io/badge/Linkedin-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/company/european-open-source)

#### [CODE OF CONDUCT](CODE_OF_CONDUCT.md)
