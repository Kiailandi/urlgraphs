import tsm


def main():
    # input da file, leggi parametri da CLI
    proc = tsm.Processor(timeout=30)
    for url in proc.run():
        # gestisci alias, aggiungi a file se serve

if __name__ == "__main__":
    main()