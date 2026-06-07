# Recommended Next Steps

1. Test with your actual bank CSV — run the app, import a real file, tune the profile (column indices, date format, encoding)
2. Category grouping in summary — aggregate income/expenses by learned category per month
3. Export — CSV or PDF summary export for a month
4. Chart view — income vs. expenses bar chart per month (PySide6's QChart or matplotlib embedded)
5. Bug: doesn't yet get less from month to month review, need to approve everything again (although with
pre-filled category)
6. ignored stuff should also be 'learned'

## Done (v0.2)

- Guided month-by-month review dialog (`Ctrl+R`) for `pending` and `anomaly` transactions
- Per-payee category learning and pre-fill on import
- Review keyboard shortcuts: **A** approve, **I** ignore, **X** anomaly
