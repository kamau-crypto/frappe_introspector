from hash import populate_range, setup_db


def main():
    conn = setup_db()
    # Already prefixed numbers are in the range of 0722, next is the 0718 category.
    # Safaricom Phone numbers are redefined within the ranges of
    # 1. 0720 to 0729. (0722 ✅ ) Done...
    # 1. 0700 to 0709
    # 2. 0710 to 0719. (0718 ✅) Done...
    # 3. 0740 to 0743, 0745, 0746, 0748.
    # 4. 0757 to 0759
    # 5. 0768 to 0769
    # 6. 0790 to 0799
    # 7. 0110 to 0111. From 2021 onwards coupled with the list below..
    # 8. 0112 to 0115
    populate_range(conn, 718)


main()
