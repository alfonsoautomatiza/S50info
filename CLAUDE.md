# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a SAGE50 database management tool (`tool-sage50`) that provides SQL execution capabilities and database administration functions for SAGE50 ERP systems. The tool connects to SQL Server databases used by SAGE50 and allows execution of SQL queries, database resets, and license management.

## Build and Development Commands

### Build Commands
- **Primary build (PowerShell)**: `.\@hacer.ps1` - Builds Cython extensions, copies files to exe/ directory, runs PyInstaller, and creates a password-protected ZIP distribution
- **Alternative build (Batch)**: `hacer.bat` - Simplified build process that builds Cython extensions and runs PyInstaller
- **Update script**: `update.bat` - Handles application updates with FTP download functionality

### Development Setup
- Uses `uv` for Python package management (uv.lock present)
- Requires Python 3.13+ (specified in pyproject.toml)
- Cython extensions in `c/Capi.py` need to be built before running: `python c/Capi.py build_ext --inplace`

## Architecture

### Core Components
- **s50info.py**: Main entry point with CLI interface using argparse. Handles command-line arguments for different operations (SQL execution, database reset, license key generation)
- **proceso.py**: Core business logic class that orchestrates SAGE50 API operations, database connections, and result formatting
- **libsage50**: External library module that provides the SAGE50 API interface
- **libwertyupdate**: Handles application update checking and functionality
- **libwertyconfig**: Manages license validation and configuration

### Key Features
- Database connection management to SAGE50 SQL Server instances
- SQL query execution with results exported to formatted text files
- Database reset functionality (truncates connect and log tables)
- License validation and SQL password generation
- Multi-company/year support through "comunes" database configuration

### Configuration
- **config.ini**: Contains database connection parameters (server, credentials, ODBC driver settings)
- **s50info.spec**: PyInstaller specification for creating distributable executable with all dependencies

### Dependencies
Key external libraries: pyodbc (SQL Server connectivity), PySimpleGUI (interface), cryptography (security), httpx (HTTP client), pythonnet (.NET integration)

## Database Operations
The tool operates on SAGE50 database structure with:
- EUROWINSYS database for system configuration
- Company databases prefixed with "COMU" + company code
- Support for multiple fiscal years per company