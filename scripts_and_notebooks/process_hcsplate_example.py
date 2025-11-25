from process_hcs_omezarr import process_hcs_omezarr
from plotting_utils import create_well_plate_heatmap
import matplotlib.pyplot as plt

# Main execution
if __name__ == "__main__":

    # adapt the path to your needs
    # hcs_omezarr_path = r"F:\Github\omezarr_playground\data\WP96_4Pos_B4-10_DAPI_HCSplate.ome.zarr"
    # hcs_omezarr_path = r"F:\Github\omezarr_playground\data\WP96_4Pos_B4-10_DAPI_HCSplate.ozx"
    hcs_omezarr_path = r"F:\Testdata_Zeiss\OME_ZARR_Testfiles\384well_DAPI_sm_HCSplate.ome.zarr"

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
        num_rows=16,  # Standard 384-well plate
        num_cols=24,  # Standard 384-well plate
        title="384-Well Plate Heatmap",
        parameter="Objects",
        cmap="viridis",
        figsize=(12, 6),
        fmt=".0f",
    )
    plt.show()
