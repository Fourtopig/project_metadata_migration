Migrate Keboola project's metadata from source to a destination project.

Configration Migration - migrates all components including all Extractors, Writers, Apps, Flows, Variables, Shared codes, Transformations. It allows user to select specific components that should be migrated or skipped.

Storage Migration - migrates all storage buckets and tables (only definitions). It doesn't migrate data, only creates empty tables in the destination project. It supports Native Types if needed. 