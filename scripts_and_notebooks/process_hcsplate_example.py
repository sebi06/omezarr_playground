from process_hcs_omezarr import process_hcs_omezarr
from plotting_utils import create_well_plate_heatmap
import matplotlib.pyplot as plt

# Main execution
if __name__ == "__main__":

    # adapt the path to your needs
    # hcs_omezarr_path = r"F:\Github\omezarr_playground\data\WP96_4Pos_B4-10_DAPI_HCSplate.ome.zarr"
    hcs_omezarr_path = r"F:\Github\omezarr_playground\data\WP96_4Pos_B4-10_DAPI_HCSplate.ozx"

    # Index of the channel to analyze
    channel2analyze = 0

    # define measurement properties to extract
    measure_properties = ("label", "area", "centroid", "bbox")

    results_obj = process_hcs_omezarr(
        hcs_omezarr_path=hcs_omezarr_path, channel2analyze=channel2analyze, measure_properties=measure_properties
    )

    # Create and display heatmap visualization using the dedicated function
    fig = create_well_plate_heatmap(
        results=results_obj,
        num_rows=8,  # Standard 96-well plate
        num_cols=12,  # Standard 96-well plate
        title="96-Well Plate Heatmap",
        parameter="Objects",
        cmap="viridis",
        figsize=(12, 6),
        fmt=".0f",
    )
    plt.show()
