from core.workers import BatchSaveWorker, build_unique_batch_save_names


def test_batch_save_names_are_unique_for_matching_basenames():
    items = [
        {"name": r"C:\first\speaker.csv"},
        {"name": r"D:\second\speaker.xlsx"},
        {"name": r"D:\second\SPEAKER.tsv"},
    ]

    names = build_unique_batch_save_names(items, "png")

    assert names == ["speaker.png", "speaker_2.png", "SPEAKER_3.png"]


def test_batch_save_names_keep_outlier_suffix_before_sequence():
    items = [{"name": "sample.csv"}, {"name": "sample.xlsx"}]

    names = build_unique_batch_save_names(items, ".svg", "_filtered")

    assert names == ["sample_filtered.svg", "sample_filtered_2.svg"]


def test_cancelled_worker_does_not_emit_completed_signal():
    worker = BatchSaveWorker(
        ".",
        [],
        plot_engine=None,
        plot_params={},
        ranges=None,
        ds_settings=None,
        img_format="png",
    )
    completed = []
    cancelled = []
    worker.finished_with_count.connect(completed.append)
    worker.cancelled_with_count.connect(cancelled.append)

    worker.cancel()
    worker.run()

    assert completed == []
    assert cancelled == [0]
