/*
 * Copyright (C) 2026 Ahmed Hadjadj
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
 */

#pragma once

#include <ytkmm/table.h>

#include "ardour/types.h"
#include "editing.h"
#include "widgets/ardour_button.h"

/* Pro Tools style 2x2 edit mode block: SHUFFLE (Ripple), SPOT (Lock),
 * SLIP (Slide) and GRID (snap on/off). Skins over existing Editor actions.
 */
class PTEditModes : public Gtk::Table
{
public:
	PTEditModes ();

	void sync (ARDOUR::EditMode, Editing::SnapMode);

private:
	ArdourWidgets::ArdourButton _shuffle;
	ArdourWidgets::ArdourButton _spot;
	ArdourWidgets::ArdourButton _slip;
	ArdourWidgets::ArdourButton _grid;

	void setup (ArdourWidgets::ArdourButton&, const char* text, const char* action_group, const char* action_name);
	bool grid_press (GdkEventButton*);
};
