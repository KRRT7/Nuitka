def iter_text(page_dicts):
    for i, page_dict in enumerate(page_dicts):
        yield i, page_dict


def main():
    print(list(iter_text([{"page": 1}])))


if __name__ == "__main__":
    main()
