from pydagu import Dag


def test_roundtrip(dagu_example):
    """Test that a DAGU config can be round-tripped through loading and saving"""

    # Load the DAG from the example dict
    dag = Dag.model_validate(dagu_example)

    assert dag.model_dump(exclude_none=True, exclude_defaults=True) == dagu_example
