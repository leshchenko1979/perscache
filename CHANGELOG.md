# Changelog

## [1.1.0] - 2024-03-18

### Added
- Instance-specific caching for both sync and async class methods
- Smart detection of instance methods vs standalone functions
- Improved logging for cache operations and method detection
- Better handling of ignored parameters in instance methods

### Fixed
- Fixed cache key generation for instance methods to ensure proper instance separation
- Fixed infinite recursion issues in instance method detection
- Fixed handling of ignored parameters in instance methods
- Fixed cache invalidation for instance methods when code changes

### Changed
- Improved instance method detection to exclude built-in types
- Updated documentation with instance method caching examples
- Simplified cache key generation logic
- Enhanced debug logging for better troubleshooting

### Developer Notes
- Added comprehensive test coverage for instance method caching
- Added test cases for both sync and async instance methods
- Added tests for multiple instances of the same class
- Added tests for ignored parameters in instance methods

## [1.0.0] - Previous version

Initial release with basic caching functionality.
