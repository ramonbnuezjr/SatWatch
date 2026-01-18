# SatWatch Documentation Index

This document provides an overview of all documentation files in the SatWatch project.

## Main Documentation Files

### README.md
**Purpose:** Project overview and quick start guide  
**Audience:** All users (beginners to advanced)  
**Contents:**
- Installation instructions
- Quick start guide
- Project structure
- Basic TLE explanation
- Next steps and roadmap

**When to read:** Start here! This is the entry point for the project.

---

### QUICK_START.md
**Purpose:** Fast setup and getting started guide  
**Audience:** Users who want to run the script immediately  
**Contents:**
- Step-by-step installation
- Multiple methods to run (dashboard, command line, API)
- Example output
- Common troubleshooting
- Quick reference

**When to read:** First time using the project, or when you need a quick reminder.

---

### DASHBOARD_README.md
**Purpose:** Streamlit dashboard documentation  
**Audience:** Users wanting to use the web dashboard  
**Contents:**
- Dashboard features and capabilities
- Installation and running instructions
- Component descriptions
- Troubleshooting
- Customization options

**When to read:** When you want to use the interactive web dashboard.

---

### ARCHITECTURE.md
**Purpose:** System architecture, design philosophy, and technical decisions  
**Audience:** Developers, contributors, and technical stakeholders  
**Contents:**
- Design philosophy (deterministic vs AI/ML)
- System components and data flow
- Core libraries and technologies
- Design decisions and rationale
- Scalability considerations
- Security considerations
- Testing strategy

**When to read:** When you want to understand why SatWatch is built the way it is, or when contributing to the codebase.

---

### CODE_EXPLANATION.md
**Purpose:** Detailed line-by-line code explanation  
**Audience:** Beginners learning Python and satellite tracking  
**Contents:**
- Installation commands
- Complete function-by-function breakdown
- Line-by-line explanations with context
- How to run the script
- Troubleshooting guide
- Key concepts (TLE, Skyfield, coordinates)

**When to read:** When you want to understand exactly how the code works.

---

### TESTING_GUIDELINES.md
**Purpose:** Testing standards and best practices  
**Audience:** Developers writing or reviewing tests  
**Contents:**
- Testing framework (pytest)
- Test file organization
- Writing test patterns
- Mocking external dependencies
- Coverage goals
- Best practices

**When to read:** When writing tests or setting up test infrastructure.

---

### PROJECT_STATUS.md
**Purpose:** Current project status, what's working, and challenges faced  
**Audience:** All developers and contributors  
**Contents:**
- What's working well
- Challenges we faced and solutions
- Current implementation status
- Known limitations
- Best practices established
- Key takeaways
- Recent issues and resolution attempts

**When to read:** To understand project status, learn from past challenges, or before contributing.

---

### ERROR_RESOLUTION_LOG.md
**Purpose:** Detailed log of all errors encountered and resolution attempts  
**Audience:** Developers debugging issues or understanding error history  
**Contents:**
- Complete error log with error messages
- Root cause analysis
- All resolution attempts and results
- Current status of each issue
- Lessons learned
- Recommendations

**When to read:** When debugging issues, understanding error history, or before implementing similar features.

---

### CHANGELOG.md
**Purpose:** Change history and updates  
**Audience:** All developers and contributors  
**Contents:**
- Completed features
- Technical improvements
- Issues resolved
- Lessons learned
- Version history

**When to read:** To see what's changed recently or track project evolution.

---

### ARCHITECTURE.md
**Purpose:** System architecture and design philosophy  
**See:** ARCHITECTURE.md section above for details

---

### scaffolding-plan.md
**Purpose:** Future project structure and architecture  
**Audience:** Developers planning project expansion  
**Contents:**
- Current architecture (Phase 1)
- Future module structure
- Module responsibilities
- Data flow diagrams
- Future enhancements
- Configuration plans

**When to read:** When planning new features or refactoring.

---

### cesium/README.md
**Purpose:** CesiumJS 3D globe viewer documentation  
**Audience:** Users wanting to use the professional 3D visualization  
**Contents:**
- Quick start guide
- Data loading (sample or generated)
- Playback controls
- Technical details
- Data format specification

**When to read:** When you want to use the CesiumJS 3D globe viewer for time-animated satellite visualization.

---

## Cursor AI Rules

Located in `.cursor/rules/`, these files guide AI-assisted code generation:

### code-style.mdc
**Purpose:** Python coding conventions  
**Contents:**
- Naming conventions (snake_case, PascalCase, etc.)
- Formatting rules (PEP 8)
- Documentation standards
- Code examples

### instructions.mdc
**Purpose:** Project context for AI assistance  
**Contents:**
- Project overview
- Current phase
- Key libraries
- Data sources
- AI behavior guidelines
- Code philosophy

### testing.mdc
**Purpose:** Testing patterns for AI code generation  
**Contents:**
- Testing framework setup
- Test structure patterns
- Coverage expectations
- Mocking patterns
- Example test code

### data-handling.mdc
**Purpose:** TLE parsing and Skyfield usage patterns  
**Contents:**
- TLE format explanation
- Skyfield usage patterns
- Error handling guidelines
- Data storage patterns
- Example code patterns

---

## Configuration Files

### requirements.txt
**Purpose:** Python package dependencies  
**Contents:**
- skyfield (astronomical calculations)
- requests (HTTP requests)
- numpy (numerical computations)
- streamlit (web dashboard framework) ✅ **NEW**
- folium (interactive maps) ✅ **NEW**
- streamlit-folium (Folium integration) ✅ **NEW**

**Usage:** `pip install -r requirements.txt`

---

## Documentation Maintenance

### Keeping Documentation Updated

When making code changes:
1. Update `CODE_EXPLANATION.md` if function line numbers change
2. Update `README.md` if project structure changes
3. Update `scaffolding-plan.md` if architecture evolves
4. Update Cursor rules if coding standards change

### Documentation Standards

- All documentation uses Markdown format
- Code examples should be tested and working
- Line numbers in explanations must match actual code
- Keep explanations beginner-friendly
- Include troubleshooting sections where relevant

---

## Quick Reference

**New to the project?**
1. Read `README.md`
2. Try the dashboard: `streamlit run src/dashboard.py` (recommended)
3. Or run the script: `python src/iss_tracker_json.py --local`
4. Read `CODE_EXPLANATION.md` to understand how it works

**Writing code?**
1. Check `.cursor/rules/code-style.mdc` for conventions
2. Follow patterns in `.cursor/rules/data-handling.mdc`
3. Write tests following `TESTING_GUIDELINES.md`

**Planning features?**
1. Review `scaffolding-plan.md` for architecture
2. Check `.cursor/rules/instructions.mdc` for project context
3. Update documentation as you go

---

## Version History

- **v1.0** (Initial) - Basic ISS tracking with comprehensive documentation
- **v1.1** (January 2025) - Added Streamlit dashboard with interactive map visualization
- **v1.2** (January 2025) - Multi-satellite tracking, conjunction risk calculator
- **v2.0** (January 2026) - UI enhancements (timeline controls), CesiumJS 3D globe viewer