# Development Rules and Guidelines

## Branch Strategy

All development must follow a strict branch workflow to ensure code quality and project stability.

### Feature Branch Workflow

1. **Always develop on feature branches from main**
   - Never commit directly to main
   - Create a new feature branch for each piece of work
   - Branch from the latest main

2. **Feature branch requirements**
   - Keep branches small and focused
   - Each branch should address a single feature or fix
   - No multiple spanning features on a single branch
   - Branch names should be descriptive (e.g., `feature/bulk-add-functionality`)

3. **Testing workflow**
   - Create a draft PR to main for the feature branch
   - All feature branches must be merged into dev first
   - Test thoroughly using the dev branch
   - Only merge to main after dev testing is complete

## Pull Request Process

### Required PR Components

Every pull request must include:

1. **Code Changes**
   - Clear description of what was changed
   - Why the changes were made
   - Any breaking changes or migration notes

2. **Documentation Updates**
   - Update `AGENTS.md` if development processes change
   - Update `README.md` to reflect new features or changes
   - Keep documentation in line with actual code functionality
   - Update any other relevant documentation files

3. **Testing Evidence**
   - Describe testing performed
   - Include screenshots for UI changes
   - Note any edge cases tested
   - Confirm backward compatibility if applicable

### PR Review Checklist

- [ ] Branch is small and focused on a single feature
- [ ] Code follows existing style and patterns
- [ ] Documentation (README.md, AGENTS.md) updated
- [ ] Testing performed and documented
- [ ] No breaking changes without migration
- [ ] Responsive design maintained
- [ ] Dark mode compatibility preserved
- [ ] Accessibility considered

## Development Guidelines

### Code Quality
- Follow existing code style and conventions
- Add comments for complex logic
- Keep functions focused and modular
- Test on multiple browsers and devices

### Data Structure Changes
- Update export/import version numbers
- Provide migration logic for existing data
- Test with existing user data
- Document schema changes in README

### UI/UX Considerations
- Maintain consistent design system
- Preserve responsive design
- Ensure accessibility (keyboard navigation, screen readers)
- Test dark/light mode switching

### Analytics Development
- Maintain three-tier complexity (Simple, Medium, Advanced)
- Ensure all new data fields are included in analytics
- Test queries with various data combinations
- Provide clear user feedback for query errors
- Maintain export functionality for all query types

## Project Context

### Terminology
- **Spool**: A complete filament spool with plastic housing and filament ready for printing
- **Refill**: A roll of filament without the spool housing - can be purchased independently and used to refill empty spools
- **Refills are independent**: Can be purchased and tracked without any existing spool of that color or material
- **Conversion**: Refills can be converted to spools when loaded onto empty spool housing

### Design Philosophy
- Single-file architecture for simplicity
- Offline-first with localStorage persistence
- Optional cloud sync via Firebase
- Privacy-focused (no accounts required)
- Progressive enhancement approach

## Spoolman Integration

### Available Tools
The project includes sync tools in `tools/spoolman-sync/` for integrating with Spoolman filament management:

- **sync-filament-log-to-spoolman.py**: Syncs filament inventory from Filament Log to Spoolman
- **add-print-log.py**: Adds print usage logs to both Filament Log and Spoolman systems
- **spoolman_id_mapping.json**: Maps Filament Log spool IDs to Spoolman spool IDs

### Workflow for Adding Print Logs
When adding print logs from screenshots or printer data:

1. **Export current Filament Log data** from http://3dworkshop.local/pages/filament-log.html
2. **Run sync tool** to ensure Spoolman is up-to-date: `python tools/spoolman-sync/sync-filament-log-to-spoolman.py <export.json>`
3. **Check for duplicates** - the tool will identify similar existing entries
4. **Add print log** using: `python tools/spoolman-sync/add-print-log.py --spool-id <id> --amount <g> --date <YYYY-MM-DD> --project "<name>"`
5. **Import updated data** back into Filament Log web app

### Important Notes
- Filament Log app is the source of truth for filament inventory
- Spoolman is used for advanced filament management and integrations
- Always check for duplicates before adding new print logs
- The ID mapping file must be preserved for future operations