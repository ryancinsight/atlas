"""Tests for the Aequitas unit audit's quantity-name checks."""

from __future__ import annotations

import importlib.util
import pathlib
import sys

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "atlas-aequitas-units.py"
_SPEC = importlib.util.spec_from_file_location("atlas_aequitas_units", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
audit = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = audit
_SPEC.loader.exec_module(audit)


def member(tmp_path: pathlib.Path, body: str) -> pathlib.Path:
    """A member whose crate source is `body`."""
    source = tmp_path / "crates" / "sample" / "src"
    source.mkdir(parents=True)
    (source / "lib.rs").write_text(body, encoding="utf-8")
    (tmp_path / "Cargo.toml").write_text(
        '[package]\nname = "sample"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    return tmp_path


def test_suffix_that_disagrees_with_the_quantity_is_reported(tmp_path):
    findings = audit._misleading_suffixes(member(tmp_path, """
pub struct Helix;

impl Helix {
    /// The helix length.
    pub fn pitch_mm(&self) -> Length {
        Length::from_m(1.0)
    }
}
"""))
    assert len(findings) == 1
    assert "pitch_mm returns m, name claims mm" in findings[0]


def test_suffix_that_agrees_with_the_quantity_is_not_reported(tmp_path):
    assert audit._misleading_suffixes(member(tmp_path, """
pub struct Helix;

impl Helix {
    /// The helix length.
    pub fn pitch_m(&self) -> Length {
        Length::from_m(1.0)
    }
}
""")) == []


def test_compound_unit_names_are_not_read_as_a_single_scale(tmp_path):
    """`m_per_s` claims a velocity; reading its last token would report `s`."""
    assert audit._misleading_suffixes(member(tmp_path, """
pub struct Helix;

impl Helix {
    /// The propagation speed.
    pub fn speed_m_per_s(&self) -> Velocity {
        Velocity::from_m_per_s(1.0)
    }
}
""")) == []


def test_a_constructor_named_for_its_input_unit_is_not_an_accessor(tmp_path):
    assert audit._misleading_suffixes(member(tmp_path, """
pub fn length_mm(value: f64) -> Length {
    Length::from_m(value / 1000.0)
}
""")) == []


def test_a_return_type_without_a_canonical_unit_is_not_measured(tmp_path):
    assert audit._misleading_suffixes(member(tmp_path, """
pub struct Helix;

impl Helix {
    /// A count of turns.
    pub fn turns_n(&self) -> u32 {
        3
    }
}
""")) == []


def test_the_audit_subject_is_the_registered_member_set(tmp_path, monkeypatch):
    """A directory under `repos/` that `.gitmodules` does not record is local work."""
    modules = tmp_path / ".gitmodules"
    modules.write_text(
        '[submodule "aequitas"]\n\tpath = repos/aequitas\n', encoding="utf-8"
    )
    monkeypatch.setattr(audit, "GITMODULES", modules)
    assert audit.registered_members() == {"aequitas"}


def test_an_unreadable_member_list_falls_back_to_no_filter(monkeypatch, tmp_path):
    monkeypatch.setattr(audit, "GITMODULES", tmp_path / "absent.gitmodules")
    assert audit.registered_members() == set()
