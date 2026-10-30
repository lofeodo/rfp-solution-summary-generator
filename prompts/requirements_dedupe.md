You are cleaning up a list of requirements extracted chunk by chunk from one Request for
Proposals (RFP). Because chunks overlap and the RFP repeats itself, the same obligation
often appears several times under different IDs. Your job is to say which IDs state the
same obligation, and which IDs contradict each other. Code will do the merging and will
check your answer, so be precise with IDs.

## Groups

Put two or more IDs in one group only when they impose the **same obligation on the same
party about the same thing**. Signs of the same obligation: the same deliverable,
deadline, limit or format, restated with different words or at a different level of
detail; a stricter restatement of the same duty ("should" in one place, "must" in
another). Signs of different obligations, which must stay apart: a different number,
date, amount, page limit or party; a different deliverable or component; a general duty
and a specific one that only partly overlaps (a duty to "provide documentation" and a
duty to "provide a user manual in PDF" are different items).

For each group choose as `representative_id` the item whose text is the most specific
and complete statement of the obligation, and list every other ID of the group in
`member_ids`. Do not put the representative in `member_ids`. Every ID may appear in at
most one group across the whole answer, as representative or as member; if three items
say the same thing, make one group of three, not two groups that share an ID. IDs that
are unique need no group; do not create single-member groups. Before answering, check
that no ID appears twice.

## Conflicts

Report a conflict when two or more items contradict each other: different deadlines or
amounts for the same thing, incompatible formats, or one item forbidding what another
requires. Give the IDs and a one-sentence reason. Conflicting items must never be in the
same group. Alternatives the RFP offers as options (Oracle or, with approval, SQL Server)
and a standard next to a more specific version of the same standard are not conflicts.

If nothing duplicates and nothing conflicts, return empty lists.

## Requirements

Each line is `ID [strictness, type] text — "quote" (chunk IDs)`.

{{requirements}}
