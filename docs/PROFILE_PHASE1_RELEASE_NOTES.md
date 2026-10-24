# Profile feature deployment notes

## Included in this branch

- Profile editing for the authenticated user: username, email, phone, and avatar.
- Email normalization and duplicate-email validation.
- Avatar upload checks: JPEG, PNG, or WEBP; maximum 2 MiB; image data must be readable.
- Checked-in initial migration for the current `store` models.
- CI verifies migrations match models and runs the Django test suite.
- A limited copy deterrent on the registration page: ordinary page text is not selectable/copyable through common browser interactions, while form controls remain usable.

## Copy and screenshot limitations

The registration-page deterrent is only a user-interface obstacle. It can be bypassed using browser tools, scripts, accessibility features, or another device, and it does not protect secrets. A normal website cannot reliably block screenshots or screen recording in a browser. Screenshot blocking is available to a native Android application using Android's `FLAG_SECURE`, but NOVA MARKAT is currently a website, so that control cannot be applied from Django/HTML alone. Do not display passwords or sensitive secrets in the registration page.

## Production media-storage requirement

The current Django setting uses local filesystem storage at `MEDIA_ROOT`. This is not a durable media strategy for an ephemeral application filesystem: profile images can become unavailable after a redeploy or instance replacement unless a persistent disk is configured and mounted.

Before enabling profile-avatar uploads in production, choose and configure one of:
1. A persistent disk attached to the Render web service and mounted at the media path; or
2. An object-storage provider with private credentials stored only in Render environment variables.

Do not commit storage credentials. Test upload, retrieval, and persistence after a service restart before considering this feature production-ready.

## Database migration caution

The initial migration is checked in so deployments no longer generate migrations implicitly during the build. Before applying it to an existing production database, take a database backup and inspect the existing `django_migrations` records and schema. Confirm that `store.0001_initial` matches the migration already applied by prior builds. Do not force-reset or drop production tables.

## Release gate

This branch and its draft pull request are not merged. No Render or Netlify production deployment is authorized by this change. Review CI, verify the target database migration history, configure persistent media, then request explicit approval before merging or deploying.
