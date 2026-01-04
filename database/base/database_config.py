from database.base.models import db, run_simulation_table, run_replications_table


def initialize_db():
    db.connect(reuse_if_open=True)
    db.create_tables([run_simulation_table, run_replications_table], safe=True)
    return db


def drop_db():
    try:
        db.drop_tables([run_simulation_table, run_replications_table], safe=True)
        db.close()
    except Exception as e:
        print(f"Error while dropping: {e}")


def drop_table(model_class):
    try:
        db.drop_tables([model_class], safe=True)
        db.close()
    except Exception as e:
        print(f"Error while dropping: {e}")


def initialize_table(model_class):
    db.connect(reuse_if_open=True)
    db.create_tables([model_class], safe=True)
    return db


if __name__ == '__main__':
    drop_db()
    initialize_db()
