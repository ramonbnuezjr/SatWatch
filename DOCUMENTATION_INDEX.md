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
- Three different methods to run the script
- Example output
- Common troubleshooting
- Quick reference

**When to read:** First time using the project, or when you need a quick reminder.

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

**When to read:** To understand project status, learn from past challenges, or before contributing.

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
2. Run the script: `python src/iss_tracker.py`
3. Read `CODE_EXPLANATION.md` to understand how it works

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
