"""Offline rule checks, separate from the real GPU/data acceptance tests."""
import tempfile
from pathlib import Path
import unittest
import zipfile

from prepare_dataset import parse_voc, safe_members, source_group, split_groups


class DatasetToolsTests(unittest.TestCase):
    def xml(self, content, size=(100, 80)):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "sample.xml"
            file.write_text(content, encoding="utf-8")
            return parse_voc(file, size)

    def box_xml(self, label="bottle", bounds=(10, 20, 30, 60), width=100):
        keys = ("xmin", "ymin", "xmax", "ymax")
        return f"<annotation><filename>old.jpg</filename><size><width>{width}</width><height>80</height></size><object><name>{label}</name><bndbox>" + "".join(f"<{key}>{value}</{key}>" for key, value in zip(keys, bounds)) + "</bndbox></object></annotation>"

    def test_voc_conversion(self):
        boxes, filename = self.xml(self.box_xml())
        self.assertEqual(filename, "old.jpg")
        self.assertEqual(boxes, [[1, 0.2, 0.5, 0.2, 0.5]])

    def test_explicit_negative_xml(self):
        self.assertEqual(self.xml("<annotation><size><width>100</width><height>80</height></size></annotation>")[0], [])

    def test_invalid_boxes(self):
        for bounds in ((0, 0, 0, 3), (-1, 0, 4, 4), (0, 0, 101, 4), (0, 0, float("nan"), 4), (0, 10, 4, 9)):
            with self.subTest(bounds=bounds), self.assertRaises(ValueError):
                self.xml(self.box_xml(bounds=bounds))

    def test_unknown_class_and_dimensions(self):
        for xml in (self.box_xml(label="unverified"), self.box_xml(width=101)):
            with self.assertRaises(ValueError):
                self.xml(xml)

    def test_xml_entities_rejected(self):
        with self.assertRaises(ValueError):
            self.xml('<!DOCTYPE a [<!ENTITY x SYSTEM "file:///C:/secret">]><annotation/>')

    def test_sequence_names(self):
        self.assertEqual(source_group("data13_283"), "data13")
        self.assertEqual(source_group("data7_DJI_0392"), "data7")
        with self.assertRaises(ValueError):
            source_group("unknown")

    def test_safe_archive(self):
        for name in ("../escape.jpg", "/escape.jpg", "C:/escape.jpg", "a\\b.jpg", "run.exe"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "bad.zip"
                with zipfile.ZipFile(path, "w") as archive:
                    info = zipfile.ZipInfo(name)
                    info.filename = name  # Windows ZipInfo otherwise normalizes the malicious test name before writing.
                    archive.writestr(info, b"test fixture")
                with zipfile.ZipFile(path) as archive, self.assertRaises(ValueError):
                    safe_members(archive)

    def test_group_split_reproducible_and_disjoint(self):
        records = [{"group": f"data{group}", "boxes": [[index % 2, .5, .5, .1, .1]]} for group in range(10) for index in range(10 + group)]
        first = split_groups(records)
        self.assertEqual(first, split_groups(records))
        self.assertEqual(set(first.values()), {"train", "val", "test"})
        self.assertEqual(len(first), 10)

    def test_cannot_split_two_groups(self):
        with self.assertRaises(ValueError):
            split_groups([{"group": "a", "boxes": []}, {"group": "b", "boxes": []}])


if __name__ == "__main__":
    unittest.main(verbosity=2)
