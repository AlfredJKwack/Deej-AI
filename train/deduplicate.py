import argparse
import csv

import pandas as pd
from tqdm import tqdm
from utils import read_playlists

# for really long playlists!
csv.field_size_limit(1000000)


if __name__ == "__main__":
    """
    Entry point for the deduplicate script.

    Deduplicates playlists and tracks.

    Args:
        --dedup_playlists_file (str): Path to save the deduplicated playlists CSV file. Default is "data/playlists_dedup.csv".
        --dedup_tracks_file (str): Path to save the deduplicated tracks CSV file. Default is "data/tracks_dedup.csv".
        --drop_missing_urls (bool): Whether to drop tracks with missing URLs. Default is True.
        --min_count (int): Number of times a track must appear in playlists to be included. Default is 10.
        --oov (str): ID for out-of-vocabulary track or None to skip. Default is None.
        --playlists_file (str): Path to the playlists CSV file. Default is "data/playlist_details.csv".
        --tracks_file (str): Path to the tracks CSV file. Default is "data/tracks.csv".

    Returns:
        None
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dedup_playlists_file",
        type=str,
        default="data/playlists_dedup.csv",
        help="Deduplicated playlists CSV file",
    )
    parser.add_argument(
        "--dedup_tracks_file",
        type=str,
        default="data/tracks_dedup.csv",
        help="Deduplicated tracks CSV file",
    )
    parser.add_argument(
        "--drop_missing_urls",
        type=bool,
        default=True,
        help="Drop tracks with missing URLs",
    )
    parser.add_argument(
        "--min_count",
        type=int,
        default=10,
        help="Number of times track must appear in playlists to be included",
    )
    parser.add_argument(
        "--oov",
        type=str,
        default=None,
        help="ID for out-of-vocabulary track or None to skip",
    )
    parser.add_argument(
        "--playlists_file",
        type=str,
        default="data/playlist_details.csv",
        help="Playlists CSV file",
    )
    parser.add_argument(
        "--tracks_file",
        type=str,
        default="data/tracks.csv",
        help="Tracks CSV file",
    )
    args = parser.parse_args()

    playlists = read_playlists(args.playlists_file)
    tracks_df = pd.read_csv(
        args.tracks_file,
        header=None,
        names=["id", "artist", "title", "url", "count"],
    )

    tracks_df = tracks_df[tracks_df["count"] >= args.min_count]
    tracks_df["url_is_empty"] = tracks_df["url"].isna() | (tracks_df["url"] == "")
    if args.drop_missing_urls:
        tracks_df = tracks_df[~tracks_df["url_is_empty"]]
    else:
        tracks_df = tracks_df.sort_values(["url_is_empty"])

    deduped_tracks_df = (
        tracks_df.groupby(["artist", "title"])
        .agg({"id": "first", "url": "first", "count": "sum"})
        .reset_index()
    )
    # grouping doesn't preserve order
    merged_df = pd.merge(
        tracks_df,
        deduped_tracks_df,
        on=["artist", "title"],
        suffixes=("_original", "_deduped"),
        how="left",
    )
    dedup = dict(zip(merged_df["id_original"], merged_df["id_deduped"]))
    deduped_playlists = {
        playlist_id: [dedup.get(track_id, args.oov) for track_id in playlist]
        for playlist_id, playlist in playlists.items()
    }

    with open(args.dedup_playlists_file, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        for key, value in tqdm(deduped_playlists.items(), desc="Writing playlists"):
            if args.oov is None:
                value = [v for v in value if v is not None]
            if len(value) > 0 and not all(v == args.oov for v in value):
                writer.writerow([key] + value)
    print(f"Writing tracks")
    deduped_tracks_df.set_index("id").to_csv(args.dedup_tracks_file, header=False)
