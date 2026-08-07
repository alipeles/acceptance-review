# Task
Walk the whole tree, not only its top level.

Nesting is not limited to one level, so a parser that descends once is
still a parser that stops early.

## Constraints
- The walk is recursive.
  - It descends into nested lists.
    - Including lists nested inside those.
  - It descends into ordered lists too.
    1. First ordered item.
    2. Second ordered item.
- A block that follows a nested list is still read.
  - The nested bullet.

  This paragraph comes after the nested list and belongs to the outer item.
- The last outer bullet.

## Scope exclusions
- Deciding what a nested block means, which is the decomposer's judgement.

## Completion expectations
- Implementation
- A test over these fixtures
