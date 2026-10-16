"""SYNTHETIC fixtures ONLY for code correctness; NOT scientific results."""
import numpy as np
import pandas as pd
import pytest
from src.python.phase_b_baci_exposure import create_exposures,country_m49,source_files
def fixture():
    panel=pd.DataFrame({"ISO3":["USA","CHN","DEU"],"Year":[2005]*3,
                        "Internet":[70.,40.,60.],"RnD":[3.,1.,2.]})
    x=pd.DataFrame({"year":[2005]*3,"importer_m49":[840]*3,
                    "exporter_m49":[156,276,999],
                    "value_thousand_usd":[80.,20.,10.]})
    mapping={"USA":840,"CHN":156,"DEU":276}
    return panel,x,mapping
def test_weighted_partner_capability_and_lag():
    p,x,m=fixture()
    got=create_exposures(x,p,m)
    assert len(got)==1
    row=got.iloc[0]
    assert row.ISO3=="USA" and row.Year==2006 and row.trade_year==2005
    assert np.isclose(row.coverage,100/110)
    assert np.isclose(row.foreign_Internet_tradeweighted_lag1,.8*40+.2*60)
    assert np.isclose(row.foreign_RnD_tradeweighted_lag1,1.2)
    assert row.eligible_peer_count==2
def test_low_coverage_is_null_not_zero():
    p,x,m=fixture()
    x.loc[x.exporter_m49==999,"value_thousand_usd"]=400
    got=create_exposures(x,p,m)
    assert np.isnan(got.iloc[0].foreign_Internet_tradeweighted_lag1)
    assert np.isnan(got.iloc[0].foreign_RnD_tradeweighted_lag1)
def test_duplicate_raw_edge_rejected():
    p,x,m=fixture()
    with pytest.raises(ValueError,match="Duplicate"):
        create_exposures(pd.concat([x,x.iloc[:1]]),p,m)
def test_negative_trade_rejected():
    p,x,m=fixture()
    x.loc[0,"value_thousand_usd"]=-3
    with pytest.raises(ValueError,match="Bad trade"):
        create_exposures(x,p,m)
def test_missing_authentic_year_files_blocked(tmp_path):
    with pytest.raises(FileNotFoundError):
        source_files(tmp_path)
def test_no_guessing_unsupported_country():
    with pytest.raises(ValueError):
        country_m49(["ZZZ"])
def test_m49_verified_mapping():
    x=country_m49(["USA","CHN","DEU"])
    assert x=={"USA":840,"CHN":156,"DEU":276}
