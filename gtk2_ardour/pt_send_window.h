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

#include <memory>

#include <ytkmm/box.h>

#include "pbd/signals.h"
#include "widgets/ardour_button.h"

#include "ardour_window.h"
#include "gain_meter.h"
#include "panner_ui.h"

namespace ARDOUR {
	class Send;
	class Session;
}

/* Pro Tools style floating send window for aux (internal) sends: level
 * fader + meter, polarity, panner. Unlike SendUI it does not need an IO
 * (InternalSend has none), which is why ProcessorBox never opens a
 * SendUIWindow for aux sends. MasterMix phase 2.
 */
class PTSendWindow : public ArdourWindow
{
public:
	PTSendWindow (ARDOUR::Session*, std::shared_ptr<ARDOUR::Send>, const std::string& track_name);
	~PTSendWindow ();

private:
	std::shared_ptr<ARDOUR::Send> _send;

	Gtk::HBox                   _hbox;
	Gtk::VBox                   _vbox;
	GainMeter                   _gpm;
	ArdourWidgets::ArdourButton _invert_button;
	PannerUI                    _panners;

	sigc::connection _fast_screen_update_connection;

	void fast_update ();
	bool invert_press (GdkEventButton*);
	bool invert_release (GdkEventButton*);
};
