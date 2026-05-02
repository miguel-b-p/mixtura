package ui

import "testing"

func TestPackagePageBounds(t *testing.T) {
	tests := []struct {
		name     string
		total    int
		page     int
		pageSize int
		wantFrom int
		wantTo   int
	}{
		{name: "less than page", total: 9, page: 0, pageSize: 10, wantFrom: 0, wantTo: 9},
		{name: "exact page", total: 10, page: 0, pageSize: 10, wantFrom: 0, wantTo: 10},
		{name: "second partial page", total: 11, page: 1, pageSize: 10, wantFrom: 10, wantTo: 11},
		{name: "large middle page", total: 905, page: 89, pageSize: 10, wantFrom: 890, wantTo: 900},
		{name: "past end", total: 11, page: 2, pageSize: 10, wantFrom: 11, wantTo: 11},
		{name: "default size", total: 12, page: 1, pageSize: 0, wantFrom: 10, wantTo: 12},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			gotFrom, gotTo := PackagePageBounds(test.total, test.page, test.pageSize)
			if gotFrom != test.wantFrom || gotTo != test.wantTo {
				t.Fatalf("PackagePageBounds(%d, %d, %d) = %d, %d; want %d, %d", test.total, test.page, test.pageSize, gotFrom, gotTo, test.wantFrom, test.wantTo)
			}
		})
	}
}
