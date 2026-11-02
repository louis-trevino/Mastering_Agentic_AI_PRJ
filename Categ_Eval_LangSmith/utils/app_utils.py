import csv 

def get_tuples_from_csv(filename: str, with_header=False) -> list[tuple[str, str]] :
    tuples_list = []

    with open(filename, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        
        if with_header:
            header = next(reader) # skip
        
        for row in reader:
            if not row:
                continue
            rr = tuple(row)
            # print(f"{rr}")
            tuples_list.append(rr)

    return tuples_list
